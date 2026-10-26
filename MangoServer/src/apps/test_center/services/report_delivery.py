import html
from src.apps.system.schemas.notice import EmailNoticeModel, FeiShuNoticeModel, WeChatNoticeModel, DingDingNoticeModel
from src.apps.system.services.notice import EmailSend, FeiShuSend, WeChatSend, DingDingSend, ReportFailureRenderer

from src.apps.test_center.exceptions import REPORT_ARTIFACT_FAILED, REPORT_LOCAL_LINK_UNAVAILABLE, TestCenterError
from src.apps.test_center.services.offline_report import OfflineReportService
from src.common.logging import log


class ReportDeliveryService:
    """各通知渠道统一附加离线链接；生成或上传失败不阻塞原通知。"""

    def __init__(self, config):
        self.config = config
        self.filename, self.content, self.note = '', b'', ''
        self._links = None
        self._links_failed = False

    @classmethod
    def prepare(cls, kind, source_id, notice):
        try:
            config = OfflineReportService.config()
        except Exception as error:
            log.system.warning(f'离线报告配置不可用，保留原通知：type={type(error).__name__}')
            return None
        if not config.enabled or not any((notice.mail, notice.work_weixin, notice.feishu, notice.dingding)):
            return None
        session = cls(config)
        try:
            session.filename, session.content = OfflineReportService.render(kind, source_id, config)
        except Exception as error:
            session.note = '离线报告生成失败或受报告保留策略限制，本次发送在线报告。'
            log.system.warning(f'离线报告降级：source={kind.value}:{source_id}, type={type(error).__name__}')
        return session

    def links(self):
        if self._links_failed:
            raise TestCenterError(REPORT_ARTIFACT_FAILED)
        if self._links is None:
            try:
                self._links = OfflineReportService.upload_links(self.config, self.filename, self.content)
            except Exception:
                self._links_failed = True
                raise
        return self._links

    @staticmethod
    def add_feishu_access_section(card, online_url, links):
        options = []
        if online_url:
            options.append(('platform', '查看平台报告（需要内网访问）', online_url))
        if links.get('查看离线报告'):
            options.append(('preview', '查看离线报告', links['查看离线报告']))
        if links.get('下载 HTML'):
            options.append(('download', '下载 HTML', links['下载 HTML']))
        if not options:
            return
        # 合并原来的分散按钮，保留其他与报告访问无关的卡片操作。
        urls = {online_url, *links.values()}
        elements = []
        for item in card['elements']:
            if item.get('tag') == 'action':
                actions = [action for action in item.get('actions', []) if action.get('url') not in urls]
                if not actions:
                    continue
                item = {**item, 'actions': actions}
            elements.append(item)
        elements.extend([
            {'tag': 'hr'},
            {'tag': 'action', 'layout': 'trisection' if len(options) == 3 else 'flow', 'actions': [
                {'tag': 'button', 'text': {'tag': 'plain_text', 'content': label},
                 'type': 'primary' if key == 'platform' else 'default', 'url': url}
                for key, label, url in options
            ]},
        ])
        card['elements'] = elements

    def send(self, notice, platform_name, online_url, mail_config, suite_report=None, group_builder=None):
        failures = []
        links, note = {}, self.note
        if not note:
            try:
                links = self.links()
            except Exception as error:
                note = error.msg if isinstance(error, TestCenterError) and error.code == REPORT_LOCAL_LINK_UNAVAILABLE.code else '离线报告生成失败，本次发送在线报告。'
        for channel, target in (('mail', notice.mail), ('wechat', notice.work_weixin), ('feishu', notice.feishu), ('dingding', notice.dingding)):
            if not target:
                continue
            try:
                if channel == 'mail':
                    sender = EmailSend(EmailNoticeModel(**mail_config(), send_list=target), suite_report, online_url, platform_name=platform_name)
                    content = group_builder.build_email_html() if group_builder else sender.build_test_report_html()
                    extra = ''.join(f'<p><a href="{html.escape(url, quote=True)}">{html.escape(label)}</a></p>' for label, url in links.items())
                    content += extra + (f'<p>{html.escape(note)}</p>' if note else '')
                    sender.send_mail(group_builder.build_title() if group_builder else sender.build_test_report_title(), content, subtype='html')
                elif channel in ('wechat', 'dingding'):
                    sender_type, model_type = (WeChatSend, WeChatNoticeModel) if channel == 'wechat' else (DingDingSend, DingDingNoticeModel)
                    sender = sender_type(model_type(webhook=target), suite_report, online_url, platform_name=platform_name)
                    content = group_builder.build_wechat_markdown(False) if group_builder else sender.build_test_report_markdown(False)
                    content += ''.join(f'\n[{label}]({url})' for label, url in links.items()) + (f'\n{note}' if note else '')
                    source = group_builder if group_builder else suite_report
                    if source is not None:
                        content = ReportFailureRenderer.markdown(content, source.failure_details, source.failure_details_note)
                    sender.send_markdown(content)
                else:
                    sender = FeiShuSend(FeiShuNoticeModel(webhook=target), suite_report, online_url, platform_name=platform_name)
                    card = group_builder.build_feishu_card() if group_builder else sender.build_test_report_card()
                    self.add_feishu_access_section(card, group_builder.group_report_url() if group_builder else online_url, links)
                    if note:
                        card['elements'].append({'tag': 'div', 'text': {'tag': 'plain_text', 'content': note}})
                    sender.send_interactive_card(card)
            except Exception as error:
                failures.append(channel)
                log.system.warning(f'离线报告通知失败：channel={channel}, type={type(error).__name__}')
        if failures:
            raise TestCenterError(REPORT_ARTIFACT_FAILED)
