export type GuideField = { label: string; value: string }
export type GuideExample = {
  title: string
  actual: string
  score: number | null
  outcome: string
  reason: string
  fields?: GuideField[]
}
export type GraderGuide = {
  versions: number[]
  purpose: string
  steps: string[]
  scoring: string
  boundary: string
  fields: GuideField[]
  examples: GuideExample[]
}

// Illustrative cases only. Switching cases never invokes an API or model.
export const graderGuides: Record<string, GraderGuide> = {
  memory_qa: {
    versions: [2], purpose: '检查最终回答有没有答对、编造事实或漏答。适合接口或脚本已经给出答案的场景。',
    steps: ['读取问题、标准答案和原文证据。', '由评分 AI 逐项核对必要事实，检查时间、主体、否定和无依据的内容。', '代码核对引用与核对项是否完整，再给出正确、幻觉、遗漏或无效结果。'],
    scoring: '正确且完整得 100 分；幻觉或遗漏得 0 分。两种错误同时出现时归为幻觉。',
    boundary: '来源矛盾无法消解、引用不存在或核对项缺失时不计分。模型自报置信度仅供参考。',
    fields: [{ label: '问题', value: 'Alice 现在住哪里，什么时候搬去的？' }, { label: '原文证据', value: 'Alice 1 月住上海，2 月 1 日搬到北京，此后没有再次搬家。' }, { label: '标准答案', value: '现在住北京，2 月 1 日搬去。' }],
    examples: [
      { title: '回答正确', actual: '她目前住在北京，是 2 月 1 日搬过去的。', score: 100, outcome: '正确', reason: '住址与时间都正确，允许同义表述。' },
      { title: '事实错误', actual: 'Alice 现在住上海，2 月 1 日搬去的。', score: 0, outcome: '幻觉', reason: '把历史住址当作当前住址，与最新证据矛盾。' },
      { title: '信息遗漏', actual: 'Alice 现在住北京。', score: 0, outcome: '遗漏', reason: '住址正确，但问题还要求搬家时间，缺少一个必要事实。' },
      { title: '无法判定', actual: 'Alice 现在住北京，2 月 1 日搬去。', score: null, outcome: '无效', reason: '来源对同一时刻的住址互相矛盾，无法可靠判定；不能直接算作答错。', fields: [{ label: '原文证据', value: `记录一：2 月 1 日 Alice 搬到北京。
记录二：同一时刻 Alice 搬到广州。两条记录没有先后或更正标记。` }] },
    ],
  },
  memory_extraction: {
    versions: [1], purpose: '检查从对话中提取的记忆是否完整，以及提取出的事实有没有依据。',
    steps: ['逐项读取标准记忆、实际提取的记忆和来源原文。', '评分 AI 分别检查标准记忆被覆盖多少、实际记忆有多少得到原文支持。', '代码计算事实准确率（Precision）、标准覆盖率（Recall）及两者的 F1。'],
    scoring: '完整支持计 1，部分支持计 0.5，遗漏、矛盾或无依据计 0。主分数为 F1 × 100，不是逐字匹配。',
    boundary: '真实但未列入标准的额外记忆不会仅因不在标准中被判为幻觉。来源无法核对时不计分。',
    fields: [{ label: '原文证据', value: '我的名字是 Alice，现在住北京。' }, { label: '标准记忆', value: `姓名是 Alice
现住北京` }],
    examples: [
      { title: '完整提取', actual: `姓名：Alice
当前住址：北京`, score: 100, outcome: 'F1 满分', reason: '准确率 100%，覆盖率 100%，F1 为 100%。' },
      { title: '少提一条', actual: '姓名：Alice', score: 66.67, outcome: '部分覆盖', reason: '提取的内容都正确，准确率 100%；两项标准只覆盖一项，覆盖率 50%，F1 约 66.67%。' },
      { title: '提取出错误事实', actual: `姓名：Alice
职业：医生`, score: 50, outcome: '含无依据事实', reason: '两个实际记忆只有姓名有依据，准确率 50%；标准住址遗漏，覆盖率 50%，F1 为 50%。' },
    ],
  },
  memory_update: {
    versions: [1], purpose: '检查新事实出现后，记忆是否真正更新，并避免旧、新事实同时被当作当前状态。',
    steps: ['读取更新前的事实、更新后的标准事实和来源原文。', '评分 AI 核对新事实是否完整生效，以及旧事实被替换还是明确标记为历史。', '代码汇总为正确、幻觉、遗漏；无法核对时标为无效。'],
    scoring: '正确更新得 100 分；遗漏更新或更新出错误事实得 0 分。历史事实可以保留，但必须和当前状态区分。',
    boundary: '只保留旧值属于未更新；正确新值和过时旧值都标为当前状态时属于冲突。',
    fields: [{ label: '更新前', value: 'Alice 现在住上海。' }, { label: '新证据', value: 'Alice 2 月 1 日从上海搬到北京。' }, { label: '更新目标', value: 'Alice 现在住北京。' }],
    examples: [
      { title: '正确更新', actual: 'Alice 现在住北京。', score: 100, outcome: '正确', reason: '当前住址已经由上海更新为北京。' },
      { title: '没有更新', actual: 'Alice 现在住上海。', score: 0, outcome: '遗漏', reason: '只保留旧事实，没有写入应生效的新事实。' },
      { title: '新旧冲突', actual: `Alice 现在住上海。
Alice 现在住北京。`, score: 0, outcome: '幻觉', reason: '旧住址与新住址同时作为当前状态存在。' },
      { title: '保留历史', actual: `Alice 1 月住上海。
Alice 现在住北京。`, score: 100, outcome: '正确', reason: '旧事实有明确历史时间，与当前状态不冲突。' },
    ],
  },
  exact_match: {
    versions: [1], purpose: '检查实际值是否与标准值完全一致，适合固定答案或明确的结构化结果。',
    steps: ['读取配置路径下的标准值和实际值。', '如果启用去除首尾空格或忽略大小写，先按配置处理文本。', '比较两个值，给出一致或不一致结果。'],
    scoring: '一致得 100 分，不一致得 0 分；不是语义判断。', boundary: '“北京”和“北京市”不会自动视为相同。',
    fields: [{ label: '标准值', value: '北京' }, { label: '示例配置', value: '直接比较，不做文本规范化' }],
    examples: [{ title: '一致', actual: '北京', score: 100, outcome: '匹配', reason: '实际文本与标准文本相同。' }, { title: '表述不同', actual: '北京市', score: 0, outcome: '不匹配', reason: '字面值不同，即使含义接近也不会自动通过。' }],
  },
  contains: {
    versions: [1], purpose: '检查回答是否包含预期关键词，用于关键词覆盖检查。',
    steps: ['读取预期关键词列表。', '在实际文本中逐个查找关键词。', '用命中的关键词数量除以总数计算分数。'],
    scoring: '分数 = 命中关键词数 ÷ 预期关键词数 × 100。示例通过阈值为 100 分。', boundary: '只检查文字出现，不理解否定或事实正确性；“不住北京”也包含“北京”。',
    fields: [{ label: '预期关键词', value: '北京、2 月 1 日' }],
    examples: [{ title: '全部命中', actual: '2 月 1 日搬到北京。', score: 100, outcome: '通过', reason: '两个关键词全部出现。' }, { title: '命中一半', actual: '已经搬到北京。', score: 50, outcome: '未通过', reason: '两个关键词只出现一个。' }],
  },
  set_match: {
    versions: [1], purpose: '比较两组结果有哪些缺失或多余，忽略排列顺序并去重。',
    steps: ['将标准列表和实际列表转换为去重后的集合。', '计算命中项、缺失项和多余项。', '根据准确率与覆盖率计算 F1。'],
    scoring: '主分数为 F1 × 100；准确率看返回项有多少正确，覆盖率看标准项找回多少。', boundary: '按实际值匹配，不做语义识别。',
    fields: [{ label: '标准集合', value: 'A、B' }],
    examples: [{ title: '顺序不同', actual: 'B、A', score: 100, outcome: '完全匹配', reason: '顺序不同不影响集合结果。' }, { title: '缺失且多余', actual: 'A、C', score: 50, outcome: '部分匹配', reason: '命中 A，缺失 B，多出 C；准确率和覆盖率均为 50%。' }],
  },
  numeric_tolerance: {
    versions: [1], purpose: '判断数值偏差是否落在允许范围内，适合金额、数量等数值结果。',
    steps: ['读取标准数值和实际数值。', '按绝对容差、相对容差计算允许误差，取两者较大值。', '比较实际误差与允许误差，给出通过结果及分数。'],
    scoring: '容差内得 100 分并通过；超出容差不通过，按当前误差公式保留部分分。部分分不代表通过。', boundary: '需要明确单位，评分器不会自动换算单位。',
    fields: [{ label: '标准数值', value: '100' }, { label: '示例配置', value: '绝对容差 2，相对容差 0' }],
    examples: [{ title: '容差以内', actual: '101', score: 100, outcome: '通过', reason: '误差 1，不超过允许误差 2。' }, { title: '超出容差', actual: '105', score: 95, outcome: '未通过', reason: '误差 5，超过允许误差 2。当前公式保留 95 分，但容差判断不通过。' }],
  },
  json_schema: {
    versions: [1], purpose: '检查返回的数据结构、字段类型和必填项，不判断业务答案是否正确。',
    steps: ['读取配置的结构要求。', '检查实际数据是否满足必填字段、类型等约束。', '全部满足则通过，否则指出不符合的字段。'],
    scoring: '符合结构要求得 100 分，否则得 0 分。', boundary: '姓名内容错误但类型正确时，结构检查仍可能通过。',
    fields: [{ label: '结构要求', value: '必须有姓名（文本）和年龄（数字）两个字段。' }],
    examples: [{ title: '结构正确', actual: `姓名：Alice（文本）
年龄：25（数字）`, score: 100, outcome: '通过', reason: '必填字段存在，类型也符合要求。' }, { title: '字段类型错误', actual: `姓名：Alice（文本）
年龄：二十五（文本）`, score: 0, outcome: '未通过', reason: '年龄要求为数字，实际却是文本。' }],
  },
  behavior: {
    versions: [1], purpose: '检查系统的行为标签是否符合预期，例如应该回答、拒答还是澄清。',
    steps: ['准备预期行为标签。', '从实际结果中提取同一种行为标签。', '精确比较两个标签。'],
    scoring: '行为标签一致得 100 分，否则得 0 分。', boundary: '不会自动从自然语言中推断行为，需要接口或脚本提供行为标签。',
    fields: [{ label: '预期行为', value: 'refuse（拒答）' }],
    examples: [{ title: '行为符合', actual: 'refuse（拒答）', score: 100, outcome: '匹配', reason: '实际行为标签为 refuse，与预期一致。' }, { title: '行为不符', actual: 'answer（回答）', score: 0, outcome: '不匹配', reason: '应该拒答，实际却选择了回答。' }],
  },
  classification: {
    versions: [1], purpose: '检查分类标签是否正确，适合情感、意图、类别等分类任务。',
    steps: ['读取标准类别和预测类别。', '逐条比较类别是否相同。', '本条给出正确与否，整次执行可汇总分类统计。'],
    scoring: '分类正确得 100 分，分类错误得 0 分。', boundary: '标签必须采用相同命名；不会自动合并同义类别。',
    fields: [{ label: '标准类别', value: 'positive（正向）' }],
    examples: [{ title: '分类正确', actual: 'positive（正向）', score: 100, outcome: '正确', reason: '预测标签与标准标签相同。' }, { title: '分类错误', actual: 'negative（负向）', score: 0, outcome: '错误', reason: '预测标签与标准标签不同。' }],
  },
  field_extraction: {
    versions: [1], purpose: '检查结构化字段是否提取正确，同时考虑漏提、多提和错误值。',
    steps: ['将标准对象和实际对象按字段路径展开。', '只有字段路径和值都一致才算命中。', '计算字段准确率、覆盖率和 F1。'],
    scoring: '主分数为字段 F1 × 100；嵌套对象继续展开，数组作为整体值比较。', boundary: '属于严格字段比较，“北京”和“北京市”不自动视为等价。',
    fields: [{ label: '标准字段', value: `姓名：Alice
住址：北京` }],
    examples: [{ title: '全部正确', actual: `姓名：Alice
住址：北京`, score: 100, outcome: '完全匹配', reason: '两个字段的名称和值都正确。' }, { title: '错一个字段', actual: `姓名：Alice
住址：上海`, score: 50, outcome: '部分匹配', reason: '两个实际字段只命中姓名，准确率与覆盖率均为 50%。' }],
  },
  ranking: {
    versions: [2], purpose: '检查相关结果是否被找回，并排在靠前的位置。',
    steps: ['准备标准相关项，并按实际返回顺序取前 K 项。', '相关项位置越靠后，对主分数的贡献越低；重复项不会重复获得增益。', '计算排序质量 NDCG，附带首个命中位置和覆盖率指标。'],
    scoring: '主分数为 NDCG@K × 100。本实现把相关性分为相关和不相关两种，不要求标准列表内的先后顺序。', boundary: '示例 K = 3，通过阈值 80 分；比较项需要采用一致的值。',
    fields: [{ label: '标准相关项', value: 'A、B' }, { label: '示例配置', value: '取前 3 项，阈值 80 分' }],
    examples: [{ title: '相关项排前面', actual: `第 1 项 A
第 2 项 B
第 3 项 X（不相关）`, score: 100, outcome: '通过', reason: '相关项占据最靠前的位置，达到理想排序。' }, { title: '无关项排第一', actual: `第 1 项 X（不相关）
第 2 项 A
第 3 项 B`, score: 69.34, outcome: '未通过', reason: '相关项都找回了，但位置后移，排序分约 69.34，低于示例阈值 80。' }],
  },
  text_token_f1: {
    versions: [1], purpose: '按词的出现次数衡量两段文本的字面重合程度。',
    steps: ['将文本转为小写，并按当前分词规则拆成词。', '按词频统计两段文本的重合部分。', '计算文本准确率、覆盖率和 F1。'],
    scoring: '主分数为词频重合 F1 × 100，不是语义相似度。', boundary: '当前规则不做中文分词，连续中文可能被当成一个词，不适合作为中文事实正确性的唯一标准。',
    fields: [{ label: '标准文本', value: 'Alice lives Beijing' }],
    examples: [{ title: '词全部相同', actual: 'alice lives Beijing', score: 100, outcome: '完全重合', reason: '忽略大小写后，三个词全部重合。' }, { title: '一个词不同', actual: 'Alice lives Shanghai', score: 66.67, outcome: '部分重合', reason: '三个词有两个重合，F1 约 66.67%；住址错误不会自动归为幻觉。' }],
  },
  model_judge: {
    versions: [1], purpose: '让评分 AI 按你配置的评分要求核对回答，适合无法用固定规则直接比较的任务。',
    steps: ['向评分 AI 提供输入、标准答案、实际输出和评分要求。', 'AI 返回分数、是否满足要求、理由及证据。', '代码校验输出；同时满足 AI 判定、分数阈值和有效性要求才通过。'],
    scoring: 'AI 按评分要求给出 0～100 分。不同评分要求得到的分数不能直接比较。', boundary: '本评分器仍将缺少证据、需复核或低于所设置信度阈值的结果标为无效。示例分数仅用于解释，不是实际 AI 评分。',
    fields: [{ label: '问题', value: 'Alice 现在住哪里？' }, { label: '标准答案', value: '北京' }, { label: '评分要求', value: '住址正确记 100，住址错误记 0；通过阈值为 80 分。' }],
    examples: [{ title: '满足要求', actual: 'Alice 现在居住在北京。', score: 100, outcome: '示意：通过', reason: '按示例评分要求，住址正确；假设裁判返回有效证据且判定通过。' }, { title: '不满足要求', actual: 'Alice 现在住上海。', score: 0, outcome: '示意：未通过', reason: '按示例评分要求，住址错误，应得 0 分。' }],
  },
}

export function getGraderGuide(key: string, version: number): GraderGuide | undefined {
  const guide = graderGuides[key]
  return guide?.versions.includes(version) ? guide : undefined
}

export function exampleFields(guide: GraderGuide, example: GuideExample): GuideField[] {
  return guide.fields.map(field => example.fields?.find(override => override.label === field.label) || field)
}
