/*
 Navicat Premium Data Transfer

 Source Server         : localhost
 Source Server Type    : MySQL
 Source Server Version : 80033
 Source Host           : localhost:3306
 Source Schema         : mango-server

 Target Server Type    : MySQL
 Target Server Version : 80033
 File Encoding         : 65001

 Date: 16/07/2023 12:11:13
*/

SET NAMES utf8mb4;
SET
    FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for api_ass
-- ----------------------------
DROP TABLE IF EXISTS `api_ass`;
CREATE TABLE `api_ass`
(
    `id`          bigint                                                         NOT NULL AUTO_INCREMENT,
    `create_time` datetime(6)                                                    NOT NULL,
    `update_time` datetime(6)                                                    NOT NULL,
    `name`        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci   NOT NULL,
    `ass_type`    smallint                                                       NULL DEFAULT NULL,
    `value`       varchar(1048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `case_id`     bigint                                                         NULL DEFAULT NULL,
    `project_id`  bigint                                                         NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `api_ass_case_id_633c14ff_fk_api_case_id` (`case_id` ASC) USING BTREE,
    INDEX `api_ass_project_id_3c5d4f3c_fk_project_id` (`project_id` ASC) USING BTREE,
    CONSTRAINT `api_ass_case_id_633c14ff_fk_api_case_id` FOREIGN KEY (`case_id`) REFERENCES `api_case` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `api_ass_project_id_3c5d4f3c_fk_project_id` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 1
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of api_ass
-- ----------------------------

-- ----------------------------
-- Table structure for api_case
-- ----------------------------
DROP TABLE IF EXISTS `api_case`;
CREATE TABLE `api_case`
(
    `id`          bigint                                                         NOT NULL AUTO_INCREMENT,
    `create_time` datetime(6)                                                    NOT NULL,
    `update_time` datetime(6)                                                    NOT NULL,
    `type`        smallint                                                       NOT NULL,
    `name`        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci   NOT NULL,
    `client`      smallint                                                       NOT NULL,
    `method`      smallint                                                       NOT NULL,
    `url`         varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `header`      varchar(2048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `body`        longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci      NULL,
    `body_type`   smallint                                                       NULL DEFAULT NULL,
    `rely`        varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci  NULL DEFAULT NULL,
    `ass`         smallint                                                       NULL DEFAULT NULL,
    `state`       smallint                                                       NULL DEFAULT NULL,
    `project_id`  bigint                                                         NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `api_case_project_id_882b99d6_fk_project_id` (`project_id` ASC) USING BTREE,
    CONSTRAINT `api_case_project_id_882b99d6_fk_project_id` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 3
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of api_case
-- ----------------------------
INSERT INTO `api_case`
VALUES (1, '2023-07-13 12:46:42.000000', '2023-07-13 12:46:38.000000', 1, '查看素材库列表', 0, 0,
        '/contentcenter/admin/materialgroup/page?total=0&current=1&size=10&descs=create_timee&shopId=${shop_id}', NULL,
        NULL, 0, NULL, NULL, 1, 1);
INSERT INTO `api_case`
VALUES (2, '2023-07-13 17:31:18.000000', '2023-07-13 17:31:21.000000', 1, '登录', 0, 1,
        '/auth/oauth/token?username=system&password=tjR%2BB82HD%2FzECGt%2F1lrqoQ%3D%3D&randomStr=${randomStr}&code=&grant_type=password&scope=server',
        '{\"Accept\": \"application/json, text/plain, */*\",\"Authorization\": \"Basic YWRtaW46YWRtaW4=\"}', NULL, NULL,
        NULL, NULL, NULL, 1);

-- ----------------------------
-- Table structure for api_case_group
-- ----------------------------
DROP TABLE IF EXISTS `api_case_group`;
CREATE TABLE `api_case_group`
(
    `id`           bigint                                                         NOT NULL AUTO_INCREMENT,
    `create_time`  datetime(6)                                                    NOT NULL,
    `update_time`  datetime(6)                                                    NOT NULL,
    `name`         varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci   NOT NULL,
    `case_id`      varchar(1048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `case_name`    varchar(1048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `state`        smallint                                                       NULL DEFAULT NULL,
    `project_id`   bigint                                                         NULL DEFAULT NULL,
    `time_name_id` bigint                                                         NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `api_case_group_project_id_17f1f75b_fk_project_id` (`project_id` ASC) USING BTREE,
    INDEX `api_case_group_time_name_id_f3222450_fk_time_tasks_id` (`time_name_id` ASC) USING BTREE,
    CONSTRAINT `api_case_group_project_id_17f1f75b_fk_project_id` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `api_case_group_time_name_id_f3222450_fk_time_tasks_id` FOREIGN KEY (`time_name_id`) REFERENCES `time_tasks` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 1
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of api_case_group
-- ----------------------------

-- ----------------------------
-- Table structure for api_public
-- ----------------------------
DROP TABLE IF EXISTS `api_public`;
CREATE TABLE `api_public`
(
    `id`          bigint                                                         NOT NULL AUTO_INCREMENT,
    `create_time` datetime(6)                                                    NOT NULL,
    `update_time` datetime(6)                                                    NOT NULL,
    `type`        smallint                                                       NULL DEFAULT NULL,
    `client`      smallint                                                       NULL DEFAULT NULL,
    `public_type` smallint                                                       NULL DEFAULT NULL,
    `name`        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci   NOT NULL,
    `key`         varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci  NULL DEFAULT NULL,
    `value`       varchar(2048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `state`       smallint                                                       NULL DEFAULT NULL,
    `project_id`  bigint                                                         NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `api_public_project_id_0376b3c2_fk_project_id` (`project_id` ASC) USING BTREE,
    CONSTRAINT `api_public_project_id_0376b3c2_fk_project_id` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 5
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of api_public
-- ----------------------------
INSERT INTO `api_public`
VALUES (1, '2023-07-13 12:48:25.000000', '2023-07-13 12:48:25.000000', 0, 0, 1, '租户id', 'tenant_id',
        '1471298785778077696', 1, 1);
INSERT INTO `api_public`
VALUES (2, '2023-07-13 12:48:25.000000', '2023-07-13 12:48:25.000000', 0, 0, 2, '店铺id', 'shop_id',
        'SELECT id FROM `shop_info` where tenant_id = \"${tenant_id}\"', 1, 1);
INSERT INTO `api_public`
VALUES (3, '2023-07-13 12:48:25.000000', '2023-07-13 12:48:25.000000', 0, 0, 3, 'tenant_id', 'header',
        '{\r\n    \"Accept\":\"application/json, text/plain, */*\",\r\n    \"Authorization\":\"Bearer ${web_token}\",\r\n  ',
        1, 1);
INSERT INTO `api_public`
VALUES (4, '2023-07-13 18:40:27.000000', '2023-07-13 18:40:30.000000', 0, 0, 0, '获取token', 'token', '2', 1, 1);

-- ----------------------------
-- Table structure for api_result
-- ----------------------------
DROP TABLE IF EXISTS `api_result`;
CREATE TABLE `api_result`
(
    `id`              bigint                                                         NOT NULL AUTO_INCREMENT,
    `create_time`     datetime(6)                                                    NOT NULL,
    `update_time`     datetime(6)                                                    NOT NULL,
    `request_url`     varchar(1048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `request_header`  longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci      NULL,
    `request_body`    longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci      NULL,
    `response_header` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci      NULL,
    `response_body`   longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci      NULL,
    `code`            int                                                            NULL DEFAULT NULL,
    `response_time`   time(6)                                                        NULL DEFAULT NULL,
    `ass_res`         smallint                                                       NULL DEFAULT NULL,
    `case_id`         bigint                                                         NULL DEFAULT NULL,
    `case_group_id`   bigint                                                         NULL DEFAULT NULL,
    `project_id`      bigint                                                         NULL DEFAULT NULL,
    `test_obj_id`     bigint                                                         NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `api_result_case_id_00d5c863_fk_api_case_id` (`case_id` ASC) USING BTREE,
    INDEX `api_result_case_group_id_ab16a135_fk_api_case_group_id` (`case_group_id` ASC) USING BTREE,
    INDEX `api_result_project_id_b9c52ddb_fk_project_id` (`project_id` ASC) USING BTREE,
    INDEX `api_result_test_obj_id_bdb3d9ff_fk_test_obj_id` (`test_obj_id` ASC) USING BTREE,
    CONSTRAINT `api_result_case_group_id_ab16a135_fk_api_case_group_id` FOREIGN KEY (`case_group_id`) REFERENCES `api_case_group` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `api_result_case_id_00d5c863_fk_api_case_id` FOREIGN KEY (`case_id`) REFERENCES `api_case` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `api_result_project_id_b9c52ddb_fk_project_id` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `api_result_test_obj_id_bdb3d9ff_fk_test_obj_id` FOREIGN KEY (`test_obj_id`) REFERENCES `test_obj` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 1
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of api_result
-- ----------------------------

-- ----------------------------
-- Table structure for auth_group
-- ----------------------------
DROP TABLE IF EXISTS `auth_group`;
CREATE TABLE `auth_group`
(
    `id`   int                                                           NOT NULL AUTO_INCREMENT,
    `name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    UNIQUE INDEX `name` (`name` ASC) USING BTREE
) ENGINE = InnoDB
  AUTO_INCREMENT = 1
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of auth_group
-- ----------------------------

-- ----------------------------
-- Table structure for auth_group_permissions
-- ----------------------------
DROP TABLE IF EXISTS `auth_group_permissions`;
CREATE TABLE `auth_group_permissions`
(
    `id`            bigint NOT NULL AUTO_INCREMENT,
    `group_id`      int    NOT NULL,
    `permission_id` int    NOT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    UNIQUE INDEX `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id` ASC, `permission_id` ASC) USING BTREE,
    INDEX `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id` ASC) USING BTREE,
    CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 1
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of auth_group_permissions
-- ----------------------------

-- ----------------------------
-- Table structure for auth_permission
-- ----------------------------
DROP TABLE IF EXISTS `auth_permission`;
CREATE TABLE `auth_permission`
(
    `id`              int                                                           NOT NULL AUTO_INCREMENT,
    `name`            varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `content_type_id` int                                                           NOT NULL,
    `codename`        varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    UNIQUE INDEX `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id` ASC, `codename` ASC) USING BTREE,
    CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 105
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of auth_permission
-- ----------------------------
INSERT INTO `auth_permission`
VALUES (1, 'Can add log entry', 1, 'add_logentry');
INSERT INTO `auth_permission`
VALUES (2, 'Can change log entry', 1, 'change_logentry');
INSERT INTO `auth_permission`
VALUES (3, 'Can delete log entry', 1, 'delete_logentry');
INSERT INTO `auth_permission`
VALUES (4, 'Can view log entry', 1, 'view_logentry');
INSERT INTO `auth_permission`
VALUES (5, 'Can add permission', 2, 'add_permission');
INSERT INTO `auth_permission`
VALUES (6, 'Can change permission', 2, 'change_permission');
INSERT INTO `auth_permission`
VALUES (7, 'Can delete permission', 2, 'delete_permission');
INSERT INTO `auth_permission`
VALUES (8, 'Can view permission', 2, 'view_permission');
INSERT INTO `auth_permission`
VALUES (9, 'Can add group', 3, 'add_group');
INSERT INTO `auth_permission`
VALUES (10, 'Can change group', 3, 'change_group');
INSERT INTO `auth_permission`
VALUES (11, 'Can delete group', 3, 'delete_group');
INSERT INTO `auth_permission`
VALUES (12, 'Can view group', 3, 'view_group');
INSERT INTO `auth_permission`
VALUES (13, 'Can add user', 4, 'add_user');
INSERT INTO `auth_permission`
VALUES (14, 'Can change user', 4, 'change_user');
INSERT INTO `auth_permission`
VALUES (15, 'Can delete user', 4, 'delete_user');
INSERT INTO `auth_permission`
VALUES (16, 'Can view user', 4, 'view_user');
INSERT INTO `auth_permission`
VALUES (17, 'Can add content type', 5, 'add_contenttype');
INSERT INTO `auth_permission`
VALUES (18, 'Can change content type', 5, 'change_contenttype');
INSERT INTO `auth_permission`
VALUES (19, 'Can delete content type', 5, 'delete_contenttype');
INSERT INTO `auth_permission`
VALUES (20, 'Can view content type', 5, 'view_contenttype');
INSERT INTO `auth_permission`
VALUES (21, 'Can add session', 6, 'add_session');
INSERT INTO `auth_permission`
VALUES (22, 'Can change session', 6, 'change_session');
INSERT INTO `auth_permission`
VALUES (23, 'Can delete session', 6, 'delete_session');
INSERT INTO `auth_permission`
VALUES (24, 'Can view session', 6, 'view_session');
INSERT INTO `auth_permission`
VALUES (25, 'Can add ui case', 7, 'add_uicase');
INSERT INTO `auth_permission`
VALUES (26, 'Can change ui case', 7, 'change_uicase');
INSERT INTO `auth_permission`
VALUES (27, 'Can delete ui case', 7, 'delete_uicase');
INSERT INTO `auth_permission`
VALUES (28, 'Can view ui case', 7, 'view_uicase');
INSERT INTO `auth_permission`
VALUES (29, 'Can add ui case group', 8, 'add_uicasegroup');
INSERT INTO `auth_permission`
VALUES (30, 'Can change ui case group', 8, 'change_uicasegroup');
INSERT INTO `auth_permission`
VALUES (31, 'Can delete ui case group', 8, 'delete_uicasegroup');
INSERT INTO `auth_permission`
VALUES (32, 'Can view ui case group', 8, 'view_uicasegroup');
INSERT INTO `auth_permission`
VALUES (33, 'Can add ui result', 9, 'add_uiresult');
INSERT INTO `auth_permission`
VALUES (34, 'Can change ui result', 9, 'change_uiresult');
INSERT INTO `auth_permission`
VALUES (35, 'Can delete ui result', 9, 'delete_uiresult');
INSERT INTO `auth_permission`
VALUES (36, 'Can view ui result', 9, 'view_uiresult');
INSERT INTO `auth_permission`
VALUES (37, 'Can add ui public', 10, 'add_uipublic');
INSERT INTO `auth_permission`
VALUES (38, 'Can change ui public', 10, 'change_uipublic');
INSERT INTO `auth_permission`
VALUES (39, 'Can delete ui public', 10, 'delete_uipublic');
INSERT INTO `auth_permission`
VALUES (40, 'Can view ui public', 10, 'view_uipublic');
INSERT INTO `auth_permission`
VALUES (41, 'Can add ui page', 11, 'add_uipage');
INSERT INTO `auth_permission`
VALUES (42, 'Can change ui page', 11, 'change_uipage');
INSERT INTO `auth_permission`
VALUES (43, 'Can delete ui page', 11, 'delete_uipage');
INSERT INTO `auth_permission`
VALUES (44, 'Can view ui page', 11, 'view_uipage');
INSERT INTO `auth_permission`
VALUES (45, 'Can add ui element', 12, 'add_uielement');
INSERT INTO `auth_permission`
VALUES (46, 'Can change ui element', 12, 'change_uielement');
INSERT INTO `auth_permission`
VALUES (47, 'Can delete ui element', 12, 'delete_uielement');
INSERT INTO `auth_permission`
VALUES (48, 'Can view ui element', 12, 'view_uielement');
INSERT INTO `auth_permission`
VALUES (49, 'Can add ui config', 13, 'add_uiconfig');
INSERT INTO `auth_permission`
VALUES (50, 'Can change ui config', 13, 'change_uiconfig');
INSERT INTO `auth_permission`
VALUES (51, 'Can delete ui config', 13, 'delete_uiconfig');
INSERT INTO `auth_permission`
VALUES (52, 'Can view ui config', 13, 'view_uiconfig');
INSERT INTO `auth_permission`
VALUES (53, 'Can add run sort', 14, 'add_runsort');
INSERT INTO `auth_permission`
VALUES (54, 'Can change run sort', 14, 'change_runsort');
INSERT INTO `auth_permission`
VALUES (55, 'Can delete run sort', 14, 'delete_runsort');
INSERT INTO `auth_permission`
VALUES (56, 'Can view run sort', 14, 'view_runsort');
INSERT INTO `auth_permission`
VALUES (57, 'Can add api case', 15, 'add_apicase');
INSERT INTO `auth_permission`
VALUES (58, 'Can change api case', 15, 'change_apicase');
INSERT INTO `auth_permission`
VALUES (59, 'Can delete api case', 15, 'delete_apicase');
INSERT INTO `auth_permission`
VALUES (60, 'Can view api case', 15, 'view_apicase');
INSERT INTO `auth_permission`
VALUES (61, 'Can add api case group', 16, 'add_apicasegroup');
INSERT INTO `auth_permission`
VALUES (62, 'Can change api case group', 16, 'change_apicasegroup');
INSERT INTO `auth_permission`
VALUES (63, 'Can delete api case group', 16, 'delete_apicasegroup');
INSERT INTO `auth_permission`
VALUES (64, 'Can view api case group', 16, 'view_apicasegroup');
INSERT INTO `auth_permission`
VALUES (65, 'Can add api result', 17, 'add_apiresult');
INSERT INTO `auth_permission`
VALUES (66, 'Can change api result', 17, 'change_apiresult');
INSERT INTO `auth_permission`
VALUES (67, 'Can delete api result', 17, 'delete_apiresult');
INSERT INTO `auth_permission`
VALUES (68, 'Can view api result', 17, 'view_apiresult');
INSERT INTO `auth_permission`
VALUES (69, 'Can add api public', 18, 'add_apipublic');
INSERT INTO `auth_permission`
VALUES (70, 'Can change api public', 18, 'change_apipublic');
INSERT INTO `auth_permission`
VALUES (71, 'Can delete api public', 18, 'delete_apipublic');
INSERT INTO `auth_permission`
VALUES (72, 'Can view api public', 18, 'view_apipublic');
INSERT INTO `auth_permission`
VALUES (73, 'Can add api assertions', 19, 'add_apiassertions');
INSERT INTO `auth_permission`
VALUES (74, 'Can change api assertions', 19, 'change_apiassertions');
INSERT INTO `auth_permission`
VALUES (75, 'Can delete api assertions', 19, 'delete_apiassertions');
INSERT INTO `auth_permission`
VALUES (76, 'Can view api assertions', 19, 'view_apiassertions');
INSERT INTO `auth_permission`
VALUES (77, 'Can add time tasks', 20, 'add_timetasks');
INSERT INTO `auth_permission`
VALUES (78, 'Can change time tasks', 20, 'change_timetasks');
INSERT INTO `auth_permission`
VALUES (79, 'Can delete time tasks', 20, 'delete_timetasks');
INSERT INTO `auth_permission`
VALUES (80, 'Can view time tasks', 20, 'view_timetasks');
INSERT INTO `auth_permission`
VALUES (81, 'Can add test object', 21, 'add_testobject');
INSERT INTO `auth_permission`
VALUES (82, 'Can change test object', 21, 'change_testobject');
INSERT INTO `auth_permission`
VALUES (83, 'Can delete test object', 21, 'delete_testobject');
INSERT INTO `auth_permission`
VALUES (84, 'Can view test object', 21, 'view_testobject');
INSERT INTO `auth_permission`
VALUES (85, 'Can add notice config', 22, 'add_noticeconfig');
INSERT INTO `auth_permission`
VALUES (86, 'Can change notice config', 22, 'change_noticeconfig');
INSERT INTO `auth_permission`
VALUES (87, 'Can delete notice config', 22, 'delete_noticeconfig');
INSERT INTO `auth_permission`
VALUES (88, 'Can view notice config', 22, 'view_noticeconfig');
INSERT INTO `auth_permission`
VALUES (89, 'Can add database', 23, 'add_database');
INSERT INTO `auth_permission`
VALUES (90, 'Can change database', 23, 'change_database');
INSERT INTO `auth_permission`
VALUES (91, 'Can delete database', 23, 'delete_database');
INSERT INTO `auth_permission`
VALUES (92, 'Can view database', 23, 'view_database');
INSERT INTO `auth_permission`
VALUES (93, 'Can add project', 24, 'add_project');
INSERT INTO `auth_permission`
VALUES (94, 'Can change project', 24, 'change_project');
INSERT INTO `auth_permission`
VALUES (95, 'Can delete project', 24, 'delete_project');
INSERT INTO `auth_permission`
VALUES (96, 'Can view project', 24, 'view_project');
INSERT INTO `auth_permission`
VALUES (97, 'Can add role', 25, 'add_role');
INSERT INTO `auth_permission`
VALUES (98, 'Can change role', 25, 'change_role');
INSERT INTO `auth_permission`
VALUES (99, 'Can delete role', 25, 'delete_role');
INSERT INTO `auth_permission`
VALUES (100, 'Can view role', 25, 'view_role');
INSERT INTO `auth_permission`
VALUES (101, 'Can add user', 26, 'add_user');
INSERT INTO `auth_permission`
VALUES (102, 'Can change user', 26, 'change_user');
INSERT INTO `auth_permission`
VALUES (103, 'Can delete user', 26, 'delete_user');
INSERT INTO `auth_permission`
VALUES (104, 'Can view user', 26, 'view_user');

-- ----------------------------
-- Table structure for auth_user
-- ----------------------------
DROP TABLE IF EXISTS `auth_user`;
CREATE TABLE `auth_user`
(
    `id`           int                                                           NOT NULL AUTO_INCREMENT,
    `password`     varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `last_login`   datetime(6)                                                   NULL DEFAULT NULL,
    `is_superuser` tinyint(1)                                                    NOT NULL,
    `username`     varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `first_name`   varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `last_name`    varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `email`        varchar(254) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `is_staff`     tinyint(1)                                                    NOT NULL,
    `is_active`    tinyint(1)                                                    NOT NULL,
    `date_joined`  datetime(6)                                                   NOT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    UNIQUE INDEX `username` (`username` ASC) USING BTREE
) ENGINE = InnoDB
  AUTO_INCREMENT = 1
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of auth_user
-- ----------------------------

-- ----------------------------
-- Table structure for auth_user_groups
-- ----------------------------
DROP TABLE IF EXISTS `auth_user_groups`;
CREATE TABLE `auth_user_groups`
(
    `id`       bigint NOT NULL AUTO_INCREMENT,
    `user_id`  int    NOT NULL,
    `group_id` int    NOT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    UNIQUE INDEX `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id` ASC, `group_id` ASC) USING BTREE,
    INDEX `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id` ASC) USING BTREE,
    CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 1
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of auth_user_groups
-- ----------------------------

-- ----------------------------
-- Table structure for auth_user_user_permissions
-- ----------------------------
DROP TABLE IF EXISTS `auth_user_user_permissions`;
CREATE TABLE `auth_user_user_permissions`
(
    `id`            bigint NOT NULL AUTO_INCREMENT,
    `user_id`       int    NOT NULL,
    `permission_id` int    NOT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    UNIQUE INDEX `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id` ASC, `permission_id` ASC) USING BTREE,
    INDEX `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id` ASC) USING BTREE,
    CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 1
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of auth_user_user_permissions
-- ----------------------------

-- ----------------------------
-- Table structure for data_base
-- ----------------------------
DROP TABLE IF EXISTS `data_base`;
CREATE TABLE `data_base`
(
    `id`          bigint                                                       NOT NULL AUTO_INCREMENT,
    `create_time` datetime(6)                                                  NOT NULL,
    `update_time` datetime(6)                                                  NOT NULL,
    `name`        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `user`        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `password`    varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `host`        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `post`        int                                                          NULL DEFAULT NULL,
    `project_id`  bigint                                                       NULL DEFAULT NULL,
    `test_obj_id` bigint                                                       NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `data_base_project_id_3757a26e_fk_project_id` (`project_id` ASC) USING BTREE,
    INDEX `data_base_test_obj_id_c99e8b24_fk_test_obj_id` (`test_obj_id` ASC) USING BTREE,
    CONSTRAINT `data_base_project_id_3757a26e_fk_project_id` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `data_base_test_obj_id_c99e8b24_fk_test_obj_id` FOREIGN KEY (`test_obj_id`) REFERENCES `test_obj` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 4
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of data_base
-- ----------------------------
INSERT INTO `data_base`
VALUES (1, '2023-07-13 12:51:02.000000', '2023-07-13 12:51:02.000000', 'joolun_mall', 'root', 'zALL_mysql1',
        '172.16.90.93', 3306, 1, 1);
INSERT INTO `data_base`
VALUES (2, '2023-07-13 12:51:02.000000', '2023-07-13 12:51:02.000000', 'joolun_mall', 'root', 'zALL_mysql1',
        '172.16.90.95', 3306, 1, 2);
INSERT INTO `data_base`
VALUES (3, '2023-07-13 12:51:02.000000', '2023-07-13 12:51:02.000000', 'joolun_mall', 'zshop', '5J86YOFzYBykNwE1',
        'rm-8vb7mc308h28823xl5o.mysql.zhangbei.rds.aliyuncs.com', 3306, 1, 3);

-- ----------------------------
-- Table structure for django_admin_log
-- ----------------------------
DROP TABLE IF EXISTS `django_admin_log`;
CREATE TABLE `django_admin_log`
(
    `id`              int                                                           NOT NULL AUTO_INCREMENT,
    `action_time`     datetime(6)                                                   NOT NULL,
    `object_id`       longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci     NULL,
    `object_repr`     varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `action_flag`     smallint UNSIGNED                                             NOT NULL,
    `change_message`  longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci     NOT NULL,
    `content_type_id` int                                                           NULL DEFAULT NULL,
    `user_id`         int                                                           NOT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id` ASC) USING BTREE,
    INDEX `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id` ASC) USING BTREE,
    CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `django_admin_log_chk_1` CHECK (`action_flag` >= 0)
) ENGINE = InnoDB
  AUTO_INCREMENT = 1
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of django_admin_log
-- ----------------------------

-- ----------------------------
-- Table structure for django_content_type
-- ----------------------------
DROP TABLE IF EXISTS `django_content_type`;
CREATE TABLE `django_content_type`
(
    `id`        int                                                           NOT NULL AUTO_INCREMENT,
    `app_label` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `model`     varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    UNIQUE INDEX `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label` ASC, `model` ASC) USING BTREE
) ENGINE = InnoDB
  AUTO_INCREMENT = 27
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of django_content_type
-- ----------------------------
INSERT INTO `django_content_type`
VALUES (1, 'admin', 'logentry');
INSERT INTO `django_content_type`
VALUES (3, 'auth', 'group');
INSERT INTO `django_content_type`
VALUES (2, 'auth', 'permission');
INSERT INTO `django_content_type`
VALUES (4, 'auth', 'user');
INSERT INTO `django_content_type`
VALUES (19, 'auto_api', 'apiassertions');
INSERT INTO `django_content_type`
VALUES (15, 'auto_api', 'apicase');
INSERT INTO `django_content_type`
VALUES (16, 'auto_api', 'apicasegroup');
INSERT INTO `django_content_type`
VALUES (18, 'auto_api', 'apipublic');
INSERT INTO `django_content_type`
VALUES (17, 'auto_api', 'apiresult');
INSERT INTO `django_content_type`
VALUES (23, 'auto_system', 'database');
INSERT INTO `django_content_type`
VALUES (22, 'auto_system', 'noticeconfig');
INSERT INTO `django_content_type`
VALUES (21, 'auto_system', 'testobject');
INSERT INTO `django_content_type`
VALUES (20, 'auto_system', 'timetasks');
INSERT INTO `django_content_type`
VALUES (14, 'auto_ui', 'runsort');
INSERT INTO `django_content_type`
VALUES (7, 'auto_ui', 'uicase');
INSERT INTO `django_content_type`
VALUES (8, 'auto_ui', 'uicasegroup');
INSERT INTO `django_content_type`
VALUES (13, 'auto_ui', 'uiconfig');
INSERT INTO `django_content_type`
VALUES (12, 'auto_ui', 'uielement');
INSERT INTO `django_content_type`
VALUES (11, 'auto_ui', 'uipage');
INSERT INTO `django_content_type`
VALUES (10, 'auto_ui', 'uipublic');
INSERT INTO `django_content_type`
VALUES (9, 'auto_ui', 'uiresult');
INSERT INTO `django_content_type`
VALUES (24, 'auto_user', 'project');
INSERT INTO `django_content_type`
VALUES (25, 'auto_user', 'role');
INSERT INTO `django_content_type`
VALUES (26, 'auto_user', 'user');
INSERT INTO `django_content_type`
VALUES (5, 'contenttypes', 'contenttype');
INSERT INTO `django_content_type`
VALUES (6, 'sessions', 'session');

-- ----------------------------
-- Table structure for django_migrations
-- ----------------------------
DROP TABLE IF EXISTS `django_migrations`;
CREATE TABLE `django_migrations`
(
    `id`      bigint                                                        NOT NULL AUTO_INCREMENT,
    `app`     varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `name`    varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `applied` datetime(6)                                                   NOT NULL,
    PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB
  AUTO_INCREMENT = 23
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of django_migrations
-- ----------------------------
INSERT INTO `django_migrations`
VALUES (1, 'contenttypes', '0001_initial', '2023-07-13 04:38:42.684274');
INSERT INTO `django_migrations`
VALUES (2, 'auth', '0001_initial', '2023-07-13 04:38:42.816279');
INSERT INTO `django_migrations`
VALUES (3, 'admin', '0001_initial', '2023-07-13 04:38:42.848348');
INSERT INTO `django_migrations`
VALUES (4, 'admin', '0002_logentry_remove_auto_add', '2023-07-13 04:38:42.854408');
INSERT INTO `django_migrations`
VALUES (5, 'admin', '0003_logentry_add_action_flag_choices', '2023-07-13 04:38:42.861405');
INSERT INTO `django_migrations`
VALUES (6, 'contenttypes', '0002_remove_content_type_name', '2023-07-13 04:38:42.899921');
INSERT INTO `django_migrations`
VALUES (7, 'auth', '0002_alter_permission_name_max_length', '2023-07-13 04:38:42.922167');
INSERT INTO `django_migrations`
VALUES (8, 'auth', '0003_alter_user_email_max_length', '2023-07-13 04:38:42.939890');
INSERT INTO `django_migrations`
VALUES (9, 'auth', '0004_alter_user_username_opts', '2023-07-13 04:38:42.945349');
INSERT INTO `django_migrations`
VALUES (10, 'auth', '0005_alter_user_last_login_null', '2023-07-13 04:38:42.969633');
INSERT INTO `django_migrations`
VALUES (11, 'auth', '0006_require_contenttypes_0002', '2023-07-13 04:38:42.971042');
INSERT INTO `django_migrations`
VALUES (12, 'auth', '0007_alter_validators_add_error_messages', '2023-07-13 04:38:42.976580');
INSERT INTO `django_migrations`
VALUES (13, 'auth', '0008_alter_user_username_max_length', '2023-07-13 04:38:43.005760');
INSERT INTO `django_migrations`
VALUES (14, 'auth', '0009_alter_user_last_name_max_length', '2023-07-13 04:38:43.035898');
INSERT INTO `django_migrations`
VALUES (15, 'auth', '0010_alter_group_name_max_length', '2023-07-13 04:38:43.050326');
INSERT INTO `django_migrations`
VALUES (16, 'auth', '0011_update_proxy_permissions', '2023-07-13 04:38:43.056650');
INSERT INTO `django_migrations`
VALUES (17, 'auth', '0012_alter_user_first_name_max_length', '2023-07-13 04:38:43.086889');
INSERT INTO `django_migrations`
VALUES (18, 'auto_user', '0001_initial', '2023-07-13 04:38:43.134822');
INSERT INTO `django_migrations`
VALUES (19, 'auto_system', '0001_initial', '2023-07-13 04:38:43.228732');
INSERT INTO `django_migrations`
VALUES (20, 'auto_api', '0001_initial', '2023-07-13 04:38:43.395630');
INSERT INTO `django_migrations`
VALUES (21, 'auto_ui', '0001_initial', '2023-07-13 04:38:43.725688');
INSERT INTO `django_migrations`
VALUES (22, 'sessions', '0001_initial', '2023-07-13 04:38:43.760996');

-- ----------------------------
-- Table structure for django_session
-- ----------------------------
DROP TABLE IF EXISTS `django_session`;
CREATE TABLE `django_session`
(
    `session_key`  varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `session_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci    NOT NULL,
    `expire_date`  datetime(6)                                                  NOT NULL,
    PRIMARY KEY (`session_key`) USING BTREE,
    INDEX `django_session_expire_date_a5c62663` (`expire_date` ASC) USING BTREE
) ENGINE = InnoDB
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of django_session
-- ----------------------------

-- ----------------------------
-- Table structure for notice_config
-- ----------------------------
DROP TABLE IF EXISTS `notice_config`;
CREATE TABLE `notice_config`
(
    `id`          bigint                                                         NOT NULL AUTO_INCREMENT,
    `create_time` datetime(6)                                                    NOT NULL,
    `update_time` datetime(6)                                                    NOT NULL,
    `type`        smallint                                                       NULL DEFAULT NULL,
    `config`      varchar(1028) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `state`       smallint                                                       NULL DEFAULT NULL,
    `project_id`  bigint                                                         NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `notice_config_project_id_7df1e426_fk_project_id` (`project_id` ASC) USING BTREE,
    CONSTRAINT `notice_config_project_id_7df1e426_fk_project_id` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 3
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of notice_config
-- ----------------------------
INSERT INTO `notice_config`
VALUES (1, '2023-07-13 12:53:51.000000', '2023-07-13 12:53:51.000000', 0,
        '{\"send_user\": \"729164035@qq.com\", \"send_list\": \"maopeng@zalldigital.com,729164035@qq.com\",\r\n         \"email_host\": \"smtp.qq.com\", \"stamp_key\": \"lqfzvjbpfcwtbecg\"}',
        0, 1);
INSERT INTO `notice_config`
VALUES (2, '2023-07-13 12:53:51.000000', '2023-07-13 12:53:51.000000', 1,
        '{\"send_user\": \"729164035@qq.com\", \"send_list\": \"maopeng@zalldigital.com,729164035@qq.com\",\r\n         \"email_host\": \"smtp.qq.com\", \"stamp_key\": \"lqfzvjbpfcwtbecg\"}',
        1, 1);

-- ----------------------------
-- Table structure for project
-- ----------------------------
DROP TABLE IF EXISTS `project`;
CREATE TABLE `project`
(
    `id`          bigint                                                       NOT NULL AUTO_INCREMENT,
    `create_time` datetime(6)                                                  NOT NULL,
    `update_time` datetime(6)                                                  NOT NULL,
    `name`        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `status`      smallint                                                     NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB
  AUTO_INCREMENT = 5
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of project
-- ----------------------------
INSERT INTO `project`
VALUES (1, '2023-07-13 12:40:26.000000', '2023-07-13 08:01:43.712886', 'Zshop', 1);
INSERT INTO `project`
VALUES (2, '2023-07-13 12:40:26.000000', '2023-07-13 12:40:26.000000', 'CDXP', 1);

-- ----------------------------
-- Table structure for role
-- ----------------------------
DROP TABLE IF EXISTS `role`;
CREATE TABLE `role`
(
    `id`          bigint                                                       NOT NULL AUTO_INCREMENT,
    `create_time` datetime(6)                                                  NOT NULL,
    `update_time` datetime(6)                                                  NOT NULL,
    `name`        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `description` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB
  AUTO_INCREMENT = 6
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of role
-- ----------------------------
INSERT INTO `role`
VALUES (1, '2023-07-13 12:39:57.000000', '2023-07-13 12:39:57.000000', '超级管理员', '超级管理员');
INSERT INTO `role`
VALUES (2, '2023-07-13 12:39:57.000000', '2023-07-13 12:39:57.000000', '测试工程师', '在平台执行自动化测试任务');
INSERT INTO `role`
VALUES (3, '2023-07-13 12:39:57.000000', '2023-07-13 12:39:57.000000', '测试经理', '管理不同测试人员的权限');
INSERT INTO `role`
VALUES (4, '2023-07-13 12:39:57.000000', '2023-07-13 12:39:57.000000', '开发', '在平台中查看报告，排查BUG');
INSERT INTO `role`
VALUES (5, '2023-07-13 12:39:57.000000', '2023-07-13 12:39:57.000000', '开发经理', '管理所有开发人员权限');

-- ----------------------------
-- Table structure for test_obj
-- ----------------------------
DROP TABLE IF EXISTS `test_obj`;
CREATE TABLE `test_obj`
(
    `id`               bigint                                                         NOT NULL AUTO_INCREMENT,
    `create_time`      datetime(6)                                                    NOT NULL,
    `update_time`      datetime(6)                                                    NOT NULL,
    `environment`      smallint                                                       NOT NULL,
    `test_type`        smallint                                                       NOT NULL,
    `name`             varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci   NOT NULL,
    `value`            varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `executor_name_id` bigint                                                         NULL DEFAULT NULL,
    `project_id`       bigint                                                         NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `test_obj_executor_name_id_ca9f0101_fk_user_id` (`executor_name_id` ASC) USING BTREE,
    INDEX `test_obj_project_id_29408db0_fk_project_id` (`project_id` ASC) USING BTREE,
    CONSTRAINT `test_obj_executor_name_id_ca9f0101_fk_user_id` FOREIGN KEY (`executor_name_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `test_obj_project_id_29408db0_fk_project_id` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 10
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of test_obj
-- ----------------------------
INSERT INTO `test_obj`
VALUES (1, '2023-07-13 12:52:27.000000', '2023-07-13 12:52:27.000000', 0, 0, 'zshop测试环境',
        'https://mall-admin-test.zalldata.cn', 1, 1);
INSERT INTO `test_obj`
VALUES (2, '2023-07-13 12:52:27.000000', '2023-07-13 12:52:27.000000', 1, 0, 'zshop预发环境',
        'https://mall-admin-pre.zalldata.cn', 1, 1);
INSERT INTO `test_obj`
VALUES (3, '2023-07-13 12:52:27.000000', '2023-07-13 08:20:28.563568', 2, 0, 'zshop生产环境',
        'http://mall-tenant.zalldata.cn', 1, 1);
INSERT INTO `test_obj`
VALUES (4, '2023-07-13 12:52:27.000000', '2023-07-13 12:52:27.000000', 0, 0, 'zdata测试环境',
        'http://newtest.zalldigital.cn', 4, 2);
INSERT INTO `test_obj`
VALUES (7, '2023-07-13 12:52:27.000000', '2023-07-13 12:52:27.000000', 2, 1, '微信-APP', 'com.tencent.mm', 1, 1);
INSERT INTO `test_obj`
VALUES (8, '2023-07-13 12:52:27.000000', '2023-07-13 12:52:27.000000', 2, 0, 'GrowKnows-线上容器',
        'https://cdxp.growknows.cn', 3, 2);
INSERT INTO `test_obj`
VALUES (9, '2023-07-13 12:52:27.000000', '2023-07-13 12:52:27.000000', 2, 1, '企业微信-APP', 'com.tencent.wework', 4, 1);

-- ----------------------------
-- Table structure for time_tasks
-- ----------------------------
DROP TABLE IF EXISTS `time_tasks`;
CREATE TABLE `time_tasks`
(
    `id`           bigint                                                       NOT NULL AUTO_INCREMENT,
    `create_time`  datetime(6)                                                  NOT NULL,
    `update_time`  datetime(6)                                                  NOT NULL,
    `name`         varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `trigger_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `month`        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `day`          varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `hour`         varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `minute`       varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    UNIQUE INDEX `name` (`name` ASC) USING BTREE
) ENGINE = InnoDB
  AUTO_INCREMENT = 5
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of time_tasks
-- ----------------------------
INSERT INTO `time_tasks`
VALUES (1, '2023-07-13 12:54:48.000000', '2023-07-13 12:54:48.000000', '每小时10分钟执行一次', 'cron', NULL, NULL, NULL, '10');
INSERT INTO `time_tasks`
VALUES (2, '2023-07-13 12:54:48.000000', '2023-07-13 12:54:48.000000', '每天18点11分执行一次', 'cron', NULL, NULL, '18', '11');
INSERT INTO `time_tasks`
VALUES (3, '2023-07-13 12:54:48.000000', '2023-07-13 12:54:48.000000', '每月25日18点12分执行一次', 'cron', NULL, '25', '18',
        '12');
INSERT INTO `time_tasks`
VALUES (4, '2023-07-13 12:54:48.000000', '2023-07-13 12:54:48.000000', '每年3月份25日18点13分执行一次', 'cron', '3', '25', '18',
        '13');

-- ----------------------------
-- Table structure for ui_case
-- ----------------------------
DROP TABLE IF EXISTS `ui_case`;
CREATE TABLE `ui_case`
(
    `id`          bigint                                                         NOT NULL AUTO_INCREMENT,
    `create_time` datetime(6)                                                    NOT NULL,
    `update_time` datetime(6)                                                    NOT NULL,
    `name`        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci   NOT NULL,
    `run_flow`    varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `state`       smallint                                                       NULL DEFAULT NULL,
    `case_type`   smallint                                                       NULL DEFAULT NULL,
    `type`        smallint                                                       NULL DEFAULT NULL,
    `project_id`  bigint                                                         NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `ui_case_project_id_bc80120e_fk_project_id` (`project_id` ASC) USING BTREE,
    CONSTRAINT `ui_case_project_id_bc80120e_fk_project_id` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 13
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of ui_case
-- ----------------------------
INSERT INTO `ui_case`
VALUES (1, '2023-07-13 12:55:47.000000', '2023-07-13 12:55:47.000000', '登录zshop并选择测试租户',
        '->账号->密码->登录按钮->点击租户->切换租户->进入后台', 0, 0, 0, 1);
INSERT INTO `ui_case`
VALUES (2, '2023-07-13 12:55:47.000000', '2023-07-13 12:55:47.000000', '新增普通商品',
        '->新增商品->店铺->选择店铺->商品分类->选择商品分类->运费模板->选择运费模板->商品分组->选择商品分组->点击基本信息->商品名称->SPU编码->商品主图->选择图片->确认选择的图片->点击商品属性->销售价->市场价->库存->SKU编码->保存商品->搜索商品名称->搜索按钮->审核->审核通过',
        0, 0, 0, 1);
INSERT INTO `ui_case`
VALUES (3, '2023-07-13 12:55:47.000000', '2023-07-13 12:55:47.000000', '关注公众号：卓尔数科新零售shop',
        '->我的->收藏->发送给芒果味的收藏->公众号-卓尔数科新零售shop->关注公众号-按钮->获取-发送消息的内容->点击-公众号右上角头像->已关注公众号->不再关注', 0, 1, 0, 1);
INSERT INTO `ui_case`
VALUES (4, '2023-07-13 12:55:47.000000', '2023-07-13 12:55:47.000000', '打开生产环境常规小程序',
        '->微信首页搜索按钮->微信首页搜索输入框->点击搜索到的小程序->小程序内容中心tab->小程序购物车tab->小程序我的tab->小程序分类tab->小程序首页tab', 0, 1, 0, 1);
INSERT INTO `ui_case`
VALUES (5, '2023-07-13 12:55:47.000000', '2023-07-13 12:55:47.000000', '登录GrowKnows租户：【勿动】线上测试', '->账号输入框->密码输入框->登录按钮',
        0, 0, 0, 2);
INSERT INTO `ui_case`
VALUES (6, '2023-07-13 12:55:47.000000', '2023-07-13 12:55:47.000000', '新建默认关注后回复',
        '->创建回复内容及规则->创建回复内容及规则-弹窗-默认关注后回复->创建文本->输入文本内容->保存文本->保存关注后回复->启用->创建回复内容及规则-弹窗-默认关注后回复', 0, 0, 0, 2);
INSERT INTO `ui_case`
VALUES (9, '2023-07-13 12:55:47.000000', '2023-07-13 12:55:47.000000', 'shop商城使用管理员登录并切换到妮维雅租户',
        '->账号->密码->登录按钮->点击租户->NIVEA微商城->进入后台', 0, 0, 0, 1);
INSERT INTO `ui_case`
VALUES (10, '2023-07-13 12:55:47.000000', '2023-07-13 12:55:47.000000', '获取首页周日数据', '->昨日->获取订单实付金额', NULL, 0, 0, 1);
INSERT INTO `ui_case`
VALUES (11, '2023-07-13 12:55:47.000000', '2023-07-13 12:55:47.000000', '登录GrowKnows租户：妮维雅', '->账号输入框->密码输入框->登录按钮',
        NULL, 0, 0, 2);
INSERT INTO `ui_case`
VALUES (12, '2023-07-13 12:55:47.000000', '2023-07-13 12:55:47.000000', '查询昨日支付订单的支付订单金额',
        '->事件分析->今日->事件->支付订单->浏览器版本->订单实付金额->订单实付金额->开始分析计算', NULL, 0, 0, 2);

-- ----------------------------
-- Table structure for ui_case_group
-- ----------------------------
DROP TABLE IF EXISTS `ui_case_group`;
CREATE TABLE `ui_case_group`
(
    `id`                 bigint                                                         NOT NULL AUTO_INCREMENT,
    `create_time`        datetime(6)                                                    NOT NULL,
    `update_time`        datetime(6)                                                    NOT NULL,
    `name`               varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci   NOT NULL,
    `case_id`            varchar(1048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `case_name`          varchar(1048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `state`              smallint                                                       NULL DEFAULT NULL,
    `case_people_id`     bigint                                                         NULL DEFAULT NULL,
    `project_id`         bigint                                                         NULL DEFAULT NULL,
    `test_obj_id`        bigint                                                         NULL DEFAULT NULL,
    `time_name_id`       bigint                                                         NULL DEFAULT NULL,
    `timing_actuator_id` bigint                                                         NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `ui_case_group_case_people_id_a818d914_fk_user_id` (`case_people_id` ASC) USING BTREE,
    INDEX `ui_case_group_project_id_e26c5f08_fk_project_id` (`project_id` ASC) USING BTREE,
    INDEX `ui_case_group_test_obj_id_30b53ba7_fk_test_obj_id` (`test_obj_id` ASC) USING BTREE,
    INDEX `ui_case_group_time_name_id_57ada98f_fk_time_tasks_id` (`time_name_id` ASC) USING BTREE,
    INDEX `ui_case_group_timing_actuator_id_9bfd2198_fk_user_id` (`timing_actuator_id` ASC) USING BTREE,
    CONSTRAINT `ui_case_group_case_people_id_a818d914_fk_user_id` FOREIGN KEY (`case_people_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `ui_case_group_project_id_e26c5f08_fk_project_id` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `ui_case_group_test_obj_id_30b53ba7_fk_test_obj_id` FOREIGN KEY (`test_obj_id`) REFERENCES `test_obj` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `ui_case_group_time_name_id_57ada98f_fk_time_tasks_id` FOREIGN KEY (`time_name_id`) REFERENCES `time_tasks` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `ui_case_group_timing_actuator_id_9bfd2198_fk_user_id` FOREIGN KEY (`timing_actuator_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 5
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of ui_case_group
-- ----------------------------
INSERT INTO `ui_case_group`
VALUES (1, '2023-07-13 12:57:20.000000', '2023-07-13 12:57:20.000000', '演示本期需求预发生产回归-新建普通商品', '[1,2]', '[登录,新建商品]', 0,
        1, 1, 2, 2, 8);
INSERT INTO `ui_case_group`
VALUES (3, '2023-07-13 12:57:20.000000', '2023-07-13 12:57:20.000000', '演示跨平台用例-公众号关注后回复全流程', '[5,6,3]',
        '[登录GrowKnows租户：【勿动】线上测试,新建默认关注后回复,关注公众号：卓尔数科新零售shop]', 0, 1, 1, 8, 2, 8);
INSERT INTO `ui_case_group`
VALUES (4, '2023-07-13 12:57:20.000000', '2023-07-13 12:57:20.000000', '演示生产巡检-核对妮维雅埋点上报金额是否正确', '[9,10,11,12]', NULL,
        NULL, 1, 2, 8, 2, 8);

-- ----------------------------
-- Table structure for ui_config
-- ----------------------------
DROP TABLE IF EXISTS `ui_config`;
CREATE TABLE `ui_config`
(
    `id`           bigint                                                         NOT NULL AUTO_INCREMENT,
    `create_time`  datetime(6)                                                    NOT NULL,
    `update_time`  datetime(6)                                                    NOT NULL,
    `local_port`   varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci   NULL DEFAULT NULL,
    `browser_path` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `equipment`    varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci   NULL DEFAULT NULL,
    `package`      varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci   NULL DEFAULT NULL,
    `user_id_id`   bigint                                                         NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `ui_config_user_id_id_7373b4ea_fk_user_id` (`user_id_id` ASC) USING BTREE,
    CONSTRAINT `ui_config_user_id_id_7373b4ea_fk_user_id` FOREIGN KEY (`user_id_id`) REFERENCES `user` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 4
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of ui_config
-- ----------------------------
INSERT INTO `ui_config`
VALUES (1, '2023-07-13 12:58:33.000000', '2023-07-13 12:58:33.000000', '9222',
        'E:\\Software\\Chrome\\Application\\chrome.exe', '7de23fdd', 'com.tencent.mm', 1);
INSERT INTO `ui_config`
VALUES (2, '2023-07-13 12:58:33.000000', '2023-07-13 12:58:33.000000', '9222',
        'C:\\Users\\Administrator\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe', '172.10.0.20:5555',
        'com.tencent.mm', 2);
INSERT INTO `ui_config`
VALUES (3, '2023-07-13 12:58:33.000000', '2023-07-13 12:58:33.000000', '9222',
        'E:\\Software\\Chrome\\Application\\chrome.exe', '8796a033', 'com.tencent.mm', 8);

-- ----------------------------
-- Table structure for ui_ele
-- ----------------------------
DROP TABLE IF EXISTS `ui_ele`;
CREATE TABLE `ui_ele`
(
    `id`          bigint                                                         NOT NULL AUTO_INCREMENT,
    `create_time` datetime(6)                                                    NOT NULL,
    `update_time` datetime(6)                                                    NOT NULL,
    `name`        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci   NOT NULL,
    `exp`         smallint                                                       NOT NULL,
    `loc`         varchar(1048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `sleep`       int                                                            NULL DEFAULT NULL,
    `sub`         int                                                            NULL DEFAULT NULL,
    `page_id`     bigint                                                         NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `ui_ele_page_id_c5a5d0e4_fk_ui_page_id` (`page_id` ASC) USING BTREE,
    CONSTRAINT `ui_ele_page_id_c5a5d0e4_fk_ui_page_id` FOREIGN KEY (`page_id`) REFERENCES `ui_page` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 154
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of ui_ele
-- ----------------------------
INSERT INTO `ui_ele`
VALUES (1, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '账号', 4, '请输入账号', NULL, NULL, 1);
INSERT INTO `ui_ele`
VALUES (2, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '密码', 4, '请输入密码', NULL, NULL, 1);
INSERT INTO `ui_ele`
VALUES (3, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '登录按钮', 0, '//button[@type=\"button\"]//span', 1,
        NULL, 1);
INSERT INTO `ui_ele`
VALUES (9, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '新增商品', 0, '//i[@class=\"el-icon-plus\"]', NULL,
        NULL, 4);
INSERT INTO `ui_ele`
VALUES (10, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '店铺', 0, '//input[@placeholder=\"请选择店铺\"]',
        NULL, 1, 4);
INSERT INTO `ui_ele`
VALUES (11, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '选择店铺', 0,
        '//div[@x-placement=\"bottom-start\"]/div/div/ul/li/span', NULL, NULL, 4);
INSERT INTO `ui_ele`
VALUES (12, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '商品分类', 0, '//input[@placeholder=\"请选择商品类目\"]',
        1, 1, 4);
INSERT INTO `ui_ele`
VALUES (13, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '选择商品分类', 0, '//span[text()=\"美妆超级牛\"]', NULL,
        NULL, 4);
INSERT INTO `ui_ele`
VALUES (14, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '运费模板', 0, '//input[@placeholder=\"请选择运费模板\"]',
        1, 0, 4);
INSERT INTO `ui_ele`
VALUES (15, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '选择运费模板', 0, '//span[text()=\"包邮\"]', NULL,
        NULL, 4);
INSERT INTO `ui_ele`
VALUES (16, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '商品分组', 0, '//input[@placeholder=\"请选择商品分组\"]',
        1, 1, 4);
INSERT INTO `ui_ele`
VALUES (17, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '选择商品分组', 0,
        '//ul[@class=\"el-scrollbar__view el-cascader-menu__list\"]/li/label/span/span', NULL, NULL, 4);
INSERT INTO `ui_ele`
VALUES (18, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '商品名称', 0, '//input[@placeholder=\"请输入商品名称\"]',
        NULL, 1, 4);
INSERT INTO `ui_ele`
VALUES (19, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', 'SPU编码', 0,
        '//input[@placeholder=\"请输入SPU编码\"]', NULL, 1, 4);
INSERT INTO `ui_ele`
VALUES (20, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '商品主图', 0,
        '//div[@disabled=\"disabled\" and @content=\"请输入商品主图\"]/div/div/ul/li', 2, NULL, 4);
INSERT INTO `ui_ele`
VALUES (21, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '选择图片', 0,
        '//div[@class=\"el-card__body\"]/div/label/span/span', NULL, 0, 4);
INSERT INTO `ui_ele`
VALUES (22, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '确认选择的图片', 0,
        '//body/div/div[@aria-label=\"素材库\"]/div/span/button/span[text()=\'确 定\']', NULL, NULL, 4);
INSERT INTO `ui_ele`
VALUES (23, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '销售价', 0, '//input[@max=\"Infinity\"]', NULL, 0,
        4);
INSERT INTO `ui_ele`
VALUES (24, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '市场价', 0, '//input[@max=\"Infinity\"]', NULL, 1,
        4);
INSERT INTO `ui_ele`
VALUES (25, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '库存', 0, '//input[@max=\"Infinity\"]', NULL, 2,
        4);
INSERT INTO `ui_ele`
VALUES (26, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', 'SKU编码', 0,
        '//div//div//div//div//div//div//div//div//div//div//div//div//div//div//div//div//div//form//div//div//div//input[@class=\"el-input__inner\"]',
        NULL, 3, 4);
INSERT INTO `ui_ele`
VALUES (27, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '保存商品', 0,
        '//section[@class=\"el-drawer__body\"]/span/button/span', NULL, NULL, 4);
INSERT INTO `ui_ele`
VALUES (28, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '审核', 0,
        '//button[@class=\"el-button el-button--text el-button--small\" and @data-v-6950c960]/span', NULL, 1, 4);
INSERT INTO `ui_ele`
VALUES (29, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '审核通过', 0,
        '//button[@class=\"el-button el-button--primary el-button--mini\"]/span', NULL, 3, 4);
INSERT INTO `ui_ele`
VALUES (30, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '点击基本信息', 0,
        '//div[@class=\"avue-group__header avue-group\"]', NULL, 0, 4);
INSERT INTO `ui_ele`
VALUES (31, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '点击商品属性', 0,
        '//div[@class=\"avue-group__header avue-group\"]', NULL, 1, 4);
INSERT INTO `ui_ele`
VALUES (32, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '积分商品', 0,
        '//*[@id=\"app\"]/div/div[2]/div[1]/div/div[2]/div[1]/div/ul/div/li[10]/ul/li[13]/span', NULL, NULL, 5);
INSERT INTO `ui_ele`
VALUES (33, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '新增', 0,
        '//button[@type=\"button\"]/i[@class=\"el-icon-plus\"]', NULL, NULL, 5);
INSERT INTO `ui_ele`
VALUES (34, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '点击商品信息', 0,
        '//div[@content=\"请选择 商品信息\"]/div/div/input', 1, 1, 5);
INSERT INTO `ui_ele`
VALUES (35, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '点击商品规格', 0,
        '//div[@content=\"请选择 商品规格\"]/div/div/input', 1, NULL, 5);
INSERT INTO `ui_ele`
VALUES (36, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '兑换积分', 0,
        '//div[@content=\"请输入 兑换积分\"]/div/div/input', NULL, NULL, 5);
INSERT INTO `ui_ele`
VALUES (37, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '活动库存', 0, '//input[@aria-label=\"请输入 活动库存\"]',
        NULL, NULL, 5);
INSERT INTO `ui_ele`
VALUES (38, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '启用', 0, '//span[@class=\"el-radio__inner\"]',
        NULL, 1, 5);
INSERT INTO `ui_ele`
VALUES (39, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '全部用户', 0, '//span[@class=\"el-radio__inner\"]',
        NULL, 2, 5);
INSERT INTO `ui_ele`
VALUES (40, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '每人限兑', 0,
        '//input[@placeholder=\"请输入每人限购数量\"]', NULL, NULL, 5);
INSERT INTO `ui_ele`
VALUES (41, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '纯积分', 0,
        '//div[@content=\"请选择 兑换类型\"]/div/div/label/span/span', 1, 0, 5);
INSERT INTO `ui_ele`
VALUES (42, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '保存', 0,
        '//span[@class=\"avue-dialog__footer avue-dialog__footer--right\"]/button/span', 2, 1, 5);
INSERT INTO `ui_ele`
VALUES (43, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '选择商品', 0,
        '//div/ul/li/span[text()=\"UI自动化1666503839\"]', NULL, NULL, 5);
INSERT INTO `ui_ele`
VALUES (44, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '选择规格', 0,
        '//div/ul/li/span[text()=\"统一规格  销售价：¥0.00\"]', NULL, NULL, 5);
INSERT INTO `ui_ele`
VALUES (45, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '点击租户', 0, '//input[@readonly=\"readonly\"]', 1,
        NULL, 1);
INSERT INTO `ui_ele`
VALUES (46, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '切换租户', 0, '//span[text()=\"常规测试\"]', 1, NULL,
        1);
INSERT INTO `ui_ele`
VALUES (48, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '进入后台', 0, '//button[@type=\"button\"]//span',
        1, NULL, 1);
INSERT INTO `ui_ele`
VALUES (62, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '基本信息', 0, '//h1[@class=\"avue-group__title\"]',
        NULL, NULL, 4);
INSERT INTO `ui_ele`
VALUES (64, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '商品属性', 0, '//h1[@class=\"avue-group__title\"]',
        NULL, 1, 4);
INSERT INTO `ui_ele`
VALUES (65, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '搜索商品名称', 0,
        '//input[@placeholder=\"请输入商品名称\"]', 1, NULL, 4);
INSERT INTO `ui_ele`
VALUES (66, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '搜索按钮', 0, '//span[text()=\"搜 索\"]', 1, NULL,
        4);
INSERT INTO `ui_ele`
VALUES (69, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '发现', 0, '//*[@text=\"发现\"]', 1, NULL, 9);
INSERT INTO `ui_ele`
VALUES (70, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '小程序', 0, '//*[@text=\"小程序\"]', 1, NULL, 9);
INSERT INTO `ui_ele`
VALUES (71, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '搜索', 0,
        '//*[@static-id=\"com.tencent.mm:id/j5t\"]', 1, NULL, 9);
INSERT INTO `ui_ele`
VALUES (75, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信首页搜索按钮', 0,
        '//*[@static-id=\"com.tencent.mm:id/j5t\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (76, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信首页搜索输入框', 0,
        '//*[@static-id=\"com.tencent.mm:id/j4t\"]/android.widget.RelativeLayout[1]', 2, NULL, 9);
INSERT INTO `ui_ele`
VALUES (77, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '点击搜索到的小程序', 0,
        '//*[@static-id=\"com.tencent.mm:id/a27\"]', 5, NULL, 9);
INSERT INTO `ui_ele`
VALUES (78, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '小程序首页tab', 0,
        '/html/body/wx-view/wx-z-tab-bar/wx-view/wx-view[2]/wx-view/wx-view[1]/wx-view/wx-view[2]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (79, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '小程序分类tab', 0,
        '/html/body/wx-view/wx-z-tab-bar/wx-view/wx-view[2]/wx-view/wx-view[2]/wx-view/wx-view[2]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (80, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '小程序内容中心tab', 0,
        '/html/body/wx-view/wx-z-tab-bar/wx-view/wx-view[2]/wx-view/wx-view[3]/wx-view/wx-view[2]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (81, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '小程序购物车tab', 0,
        '/html/body/wx-view/wx-z-tab-bar/wx-view/wx-view[2]/wx-view/wx-view[4]/wx-view/wx-view[2]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (82, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '小程序我的tab', 0,
        '/html/body/wx-view/wx-z-tab-bar/wx-view/wx-view[2]/wx-view/wx-view[5]/wx-view/wx-view[2]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (83, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信支付-零钱', 0,
        '//android.widget.ScrollView/android.view.ViewGroup[1]/android.view.ViewGroup[3]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (84, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信支付-选择零钱', 0,
        '//android.widget.ScrollView/android.view.ViewGroup[1]/android.view.ViewGroup[1]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (85, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信支付密码-数字1', 0,
        '//*[@static-id=\"com.tencent.mm:id/tenpay_keyboard_1\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (86, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信支付密码-数字2', 0,
        '//*[@static-id=\"com.tencent.mm:id/tenpay_keyboard_2\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (87, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信支付密码-数字3', 0,
        '//*[@static-id=\"com.tencent.mm:id/tenpay_keyboard_3\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (88, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信支付密码-数字4', 0,
        '//*[@static-id=\"com.tencent.mm:id/tenpay_keyboard_4\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (89, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信支付密码-数字5', 0,
        '//*[@static-id=\"com.tencent.mm:id/tenpay_keyboard_5\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (90, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信支付密码-数字6', 0,
        '//*[@static-id=\"com.tencent.mm:id/tenpay_keyboard_6\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (91, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信支付密码-数字7', 0,
        '//*[@static-id=\"com.tencent.mm:id/tenpay_keyboard_6\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (92, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信支付密码-数字8', 0,
        '//*[@static-id=\"com.tencent.mm:id/tenpay_keyboard_8\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (93, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信支付密码-数字9', 0,
        '//*[@static-id=\"com.tencent.mm:id/tenpay_keyboard_9\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (94, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信支付密码-数字0', 0,
        '//*[@static-id=\"com.tencent.mm:id/tenpay_keyboard_0\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (95, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信支付密码-删除键', 0,
        '//*[@static-id=\"com.tencent.mm:id/kh0\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (96, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '微信支付密码-关闭按钮', 0,
        '//*[@content-desc=\"关闭\"]/android.view.ViewGroup[1]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (105, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '企业微信-点击聊天列表中的芒果味', 0, '//*[@text=\"芒果味\"]',
        NULL, NULL, 10);
INSERT INTO `ui_ele`
VALUES (106, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '企业微信-点击芒果味发送的小程序', 0,
        '//*[@static-id=\"com.tencent.wework:id/j_y\"]', 4, NULL, 10);
INSERT INTO `ui_ele`
VALUES (108, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '商品列表第一个商品', 0,
        '//android.webkit.WebView/android.view.View[4]/android.view.View[1]', NULL, NULL, 10);
INSERT INTO `ui_ele`
VALUES (109, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '全局搜索商品名称', 0, '//*[@text=\"${}\"]', NULL,
        NULL, 10);
INSERT INTO `ui_ele`
VALUES (110, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '立即购买', 0, '//*[@text=\"立即购买\"]', NULL, NULL,
        10);
INSERT INTO `ui_ele`
VALUES (111, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '账号输入框', 0,
        '//input[@placeholder=\"请输入管理员分配的登录账号\"]', NULL, NULL, 13);
INSERT INTO `ui_ele`
VALUES (112, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '密码输入框', 0, '//input[@placeholder=\'请输入密码\']',
        NULL, NULL, 13);
INSERT INTO `ui_ele`
VALUES (113, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '登录按钮', 0,
        '/html[@class=\' \']/body/div[@id=\' app\']/div[@class=\'login-container\']/div[@class=\'login-content\']/div[@class=\'login-warp\']/div[@class=\'login-box\']/form[@class=\'el-form login-form el-form--label-top\']/button[@class=\'el-button login-btn el-button--success\']/span',
        NULL, NULL, 13);
INSERT INTO `ui_ele`
VALUES (114, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '创建回复内容及规则', 0,
        '//div[@class=\"app-add-btn\"]', NULL, NULL, 14);
INSERT INTO `ui_ele`
VALUES (115, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '创建文本', 0, '//span[@class=\"tip-text\"]', NULL,
        NULL, 14);
INSERT INTO `ui_ele`
VALUES (116, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '输入文本内容', 0,
        '//div[@contenteditable=\"true\"]/div', NULL, NULL, 14);
INSERT INTO `ui_ele`
VALUES (117, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '保存文本', 0,
        '//button[@class=\"el-button ml16 el-button--success el-button--small\"]', NULL, NULL, 14);
INSERT INTO `ui_ele`
VALUES (118, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '保存关注后回复', 0,
        '//div/button[@type=\"button\"]/span[text()=\"保 存\"]', NULL, NULL, 14);
INSERT INTO `ui_ele`
VALUES (119, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '启用', 0, '//div[@class=\"el-switch\"]/span',
        NULL, NULL, 14);
INSERT INTO `ui_ele`
VALUES (120, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '公众号名称', 0, '//span[@class=\"context-value\"]',
        NULL, NULL, 14);
INSERT INTO `ui_ele`
VALUES (121, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '菜单-关注后回复', 0,
        '//div[@class=\"title active\"]', NULL, NULL, 14);
INSERT INTO `ui_ele`
VALUES (122, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '事件分析', 0,
        '//div[@class=\"name\" and text()=\'事件分析\']', NULL, NULL, 48);
INSERT INTO `ui_ele`
VALUES (123, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '漏斗分析', 0,
        '//div[@class=\"name\" and text()=\'漏斗分析\']', NULL, NULL, 48);
INSERT INTO `ui_ele`
VALUES (124, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '今日', 0, '//a[text()=\'今日\']', NULL, NULL, 48);
INSERT INTO `ui_ele`
VALUES (125, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '创建回复内容及规则-弹窗-默认关注后回复', 0,
        '//div[@class=\"el-dialog__body\"]/div/div/div/h4[text()=\"默认关注回复\"]', NULL, NULL, 14);
INSERT INTO `ui_ele`
VALUES (126, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '通讯录', 0,
        '//*[@static-id=\"com.tencent.mm:id/fj3\"]/android.widget.LinearLayout[1]/android.widget.RelativeLayout[2]/android.widget.LinearLayout[1]/android.widget.TextView[1]',
        NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (127, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '公众号', 0, '//*[@text=\"公众号\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (128, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '通讯录-公众号-搜索按钮', 0,
        '//*[@static-id=\"com.tencent.mm:id/by2\"]/android.widget.LinearLayout[1]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (129, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '通讯录-公众号-搜索输入框', 0,
        '//*[@static-id=\"com.tencent.mm:id/eg6\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (130, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '通讯录-公众号-点击搜索公众号', 0,
        '//*[@static-id=\"com.tencent.mm:id/lm0\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (131, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '我的', 0, '//*[@text=\"我\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (132, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '收藏', 0, '//*[@text=\"收藏\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (133, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '发送给芒果味的收藏', 0, '//*[@text=\"芒果味\"]', NULL,
        NULL, 9);
INSERT INTO `ui_ele`
VALUES (134, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '公众号-卓尔数科新零售shop', 0,
        '//*[@static-id=\"com.tencent.mm:id/knx\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (135, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '关注公众号-按钮', 0,
        '//*[@static-id=\"com.tencent.mm:id/njr\"]', 6, NULL, 9);
INSERT INTO `ui_ele`
VALUES (136, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '获取-发送消息的内容', 0,
        '//*[@static-id=\"com.tencent.mm:id/b79\"]/android.widget.RelativeLayout[1]/android.widget.LinearLayout[1]/android.widget.LinearLayout[1]',
        NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (137, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '点击-公众号右上角头像', 0,
        '//*[@static-id=\"com.tencent.mm:id/by3\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (138, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '已关注公众号', 0,
        '//*[@static-id=\"com.tencent.mm:id/nk0\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (139, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '不再关注', 0,
        '//*[@static-id=\"com.tencent.mm:id/guw\"]', NULL, NULL, 9);
INSERT INTO `ui_ele`
VALUES (140, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '常规测试租户', 0, '//span[text()=\'常规测试商户\']', 1,
        NULL, 1);
INSERT INTO `ui_ele`
VALUES (141, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', 'NIVEA微商城', 0, '//span[text()=\'NIVEA微商城\']',
        NULL, NULL, 1);
INSERT INTO `ui_ele`
VALUES (142, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '本周页签', 0,
        '/html[@class=\' \']/body/div[@id=\' app\']/div[@class=\'avue-contail\']/div[@class=\'avue-layout\']/div[@class=\'avue-main\']/div[@class=\'el-scrollbar\']/div[@class=\'el-scrollbar__wrap\']/div[@class=\'el-scrollbar__view\']/div[@class=\'avue-view page-keep-alive\']/div[@class=\'basic-container wel-view\']/div[@class=\'el-card is-never-shadow\']/div[@class=\'el-card__body\']/div[@class=\'idx\']/div[@class=\'shippingManagement_idx\']/div[@class=\'shippingManagement\']/div[@class=\'shippingManagement_\']/div[2]',
        3, NULL, 49);
INSERT INTO `ui_ele`
VALUES (143, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '获取订单实付金额', 0,
        '/html[@class=\' \']/body/div[@id=\' app\']/div[@class=\'avue-contail\']/div[@class=\'avue-layout\']/div[@class=\'avue-main\']/div[@class=\'el-scrollbar\']/div[@class=\'el-scrollbar__wrap\']/div[@class=\'el-scrollbar__view\']/div[@class=\'avue-view page-keep-alive\']/div[@class=\'basic-container wel-view\']/div[@class=\'el-card is-never-shadow\']/div[@class=\'el-card__body\']/div[@class=\'idx\']/div[@class=\'idx_two\']/div[@class=\'idx_three\'][2]/div[@class=\'idx_three_01\'][3]/div[@class=\'idx_three_04\']/p[2]/span[1]',
        NULL, NULL, 49);
INSERT INTO `ui_ele`
VALUES (144, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '昨日', 0, '//div[@class=\"Selected\"]', 3, NULL,
        49);
INSERT INTO `ui_ele`
VALUES (145, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '全部订单', 0, '//p[text()=\'全部商品\']', NULL, NULL,
        49);
INSERT INTO `ui_ele`
VALUES (146, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '事件', 0, '//span[text()=\'事件\']', NULL, NULL,
        48);
INSERT INTO `ui_ele`
VALUES (147, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '关键字搜索', 0,
        '//ul/div/div/div/div/input[@placeholder=\"输入关键字搜索\"]', NULL, NULL, 48);
INSERT INTO `ui_ele`
VALUES (148, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '支付订单', 0, '//li[@id=\"event77373\"]', NULL,
        NULL, 48);
INSERT INTO `ui_ele`
VALUES (149, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '企业微信群ID', 0, '//span[text()=\'企业微信群ID\']',
        NULL, NULL, 48);
INSERT INTO `ui_ele`
VALUES (150, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '订单实付金额', 0, '//span[text()=\'订单实付金额\']', 1,
        NULL, 48);
INSERT INTO `ui_ele`
VALUES (152, '2023-07-13 13:01:28.000000', '2023-07-13 13:01:28.000000', '开始分析计算', 0,
        '//div[@class=\"toggle-icon-container text-white pointer\"]', 5, NULL, 48);
INSERT INTO `ui_ele`
VALUES (153, '2023-07-13 13:02:49.000000', '2023-07-13 13:02:51.000000', '浏览器版本', 0, '//span[text()=\'浏览器版本\']', NULL,
        NULL, 48);

-- ----------------------------
-- Table structure for ui_page
-- ----------------------------
DROP TABLE IF EXISTS `ui_page`;
CREATE TABLE `ui_page`
(
    `id`          bigint                                                        NOT NULL AUTO_INCREMENT,
    `create_Time` datetime(6)                                                   NOT NULL,
    `update_time` datetime(6)                                                   NOT NULL,
    `name`        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci  NOT NULL,
    `url`         varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
    `type`        smallint                                                      NOT NULL,
    `project_id`  bigint                                                        NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `ui_page_project_id_957537c3_fk_project_id` (`project_id` ASC) USING BTREE,
    CONSTRAINT `ui_page_project_id_957537c3_fk_project_id` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 50
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of ui_page
-- ----------------------------
INSERT INTO `ui_page`
VALUES (1, '2023-07-13 13:02:10.000000', '2023-07-13 13:02:10.000000', '登录', '/#/login', 0, 1);
INSERT INTO `ui_page`
VALUES (3, '2023-07-13 13:02:10.000000', '2023-07-13 13:02:10.000000', '商城模块', '/#/mall/index', 0, 1);
INSERT INTO `ui_page`
VALUES (4, '2023-07-13 13:02:10.000000', '2023-07-13 13:02:10.000000', '全部商品', '/#/mall/goods/goodsspu', 0, 1);
INSERT INTO `ui_page`
VALUES (5, '2023-07-13 13:02:10.000000', '2023-07-13 13:02:10.000000', '积分商品管理', '/#/mall/marketing/pointsmall', 0, 1);
INSERT INTO `ui_page`
VALUES (6, '2023-07-13 13:02:10.000000', '2023-07-13 13:02:10.000000', '首页', 'index', 2, 1);
INSERT INTO `ui_page`
VALUES (7, '2023-07-13 13:02:10.000000', '2023-07-13 13:02:10.000000', '拼团活动', '/#/mall/marketing/grouponinfo', 0, 1);
INSERT INTO `ui_page`
VALUES (8, '2023-07-13 13:02:10.000000', '2023-07-13 13:02:10.000000', 'N元任选', '/#/mall/marketing/optionalActivities',
        0, 1);
INSERT INTO `ui_page`
VALUES (9, '2023-07-13 13:02:10.000000', '2023-07-13 13:02:10.000000', '微信', 'com.tencent.mm', 1, 1);
INSERT INTO `ui_page`
VALUES (10, '2023-07-13 13:02:10.000000', '2023-07-13 13:02:10.000000', '支付宝', 'com.eg.android.AlipayGphone', 1, 1);
INSERT INTO `ui_page`
VALUES (11, '2023-07-13 13:02:10.000000', '2023-07-13 13:02:10.000000', '企业微信', 'com.tencent.wework', 1, 1);
INSERT INTO `ui_page`
VALUES (13, '2023-07-13 13:02:10.000000', '2023-07-13 13:02:10.000000', 'Growknows登录页面', '/login', 0, 2);
INSERT INTO `ui_page`
VALUES (14, '2023-07-13 13:02:10.000000', '2023-07-13 13:02:10.000000', '公众号-关注后回复',
        '/official/promotingTransformation/followedBy', 0, 2);
INSERT INTO `ui_page`
VALUES (48, '2023-07-13 13:02:10.000000', '2023-07-13 13:02:10.000000', '分析模型',
        '/analysis/analysisTemplate/behaviorAnalysis', 0, 2);
INSERT INTO `ui_page`
VALUES (49, '2023-07-13 13:02:10.000000', '2023-07-13 13:02:10.000000', '首页', '/#/mall/index', 0, 1);

-- ----------------------------
-- Table structure for ui_public
-- ----------------------------
DROP TABLE IF EXISTS `ui_public`;
CREATE TABLE `ui_public`
(
    `id`          bigint                                                         NOT NULL AUTO_INCREMENT,
    `create_time` datetime(6)                                                    NOT NULL,
    `update_time` datetime(6)                                                    NOT NULL,
    `type`        smallint                                                       NULL DEFAULT NULL,
    `name`        varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci   NOT NULL,
    `key`         varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci  NULL DEFAULT NULL,
    `value`       varchar(2048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `state`       smallint                                                       NULL DEFAULT NULL,
    `project_id`  bigint                                                         NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `ui_public_project_id_27031aaf_fk_project_id` (`project_id` ASC) USING BTREE,
    CONSTRAINT `ui_public_project_id_27031aaf_fk_project_id` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 1
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of ui_public
-- ----------------------------

-- ----------------------------
-- Table structure for ui_result
-- ----------------------------
DROP TABLE IF EXISTS `ui_result`;
CREATE TABLE `ui_result`
(
    `id`            bigint                                                         NOT NULL AUTO_INCREMENT,
    `create_time`   datetime(6)                                                    NOT NULL,
    `update_time`   datetime(6)                                                    NOT NULL,
    `ele_name`      varchar(1048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `existence`     smallint                                                       NULL DEFAULT NULL,
    `picture`       varchar(1048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `msg`           varchar(1048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `state`         smallint                                                       NULL DEFAULT NULL,
    `case_id`       bigint                                                         NULL DEFAULT NULL,
    `case_group_id` bigint                                                         NULL DEFAULT NULL,
    `project_id`    bigint                                                         NULL DEFAULT NULL,
    `test_obj_id`   bigint                                                         NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `ui_result_case_id_c2385cf3_fk_ui_case_id` (`case_id` ASC) USING BTREE,
    INDEX `ui_result_case_group_id_c59b5692_fk_ui_case_group_id` (`case_group_id` ASC) USING BTREE,
    INDEX `ui_result_project_id_3c6a4343_fk_project_id` (`project_id` ASC) USING BTREE,
    INDEX `ui_result_test_obj_id_f23df624_fk_test_obj_id` (`test_obj_id` ASC) USING BTREE,
    CONSTRAINT `ui_result_case_group_id_c59b5692_fk_ui_case_group_id` FOREIGN KEY (`case_group_id`) REFERENCES `ui_case_group` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `ui_result_case_id_c2385cf3_fk_ui_case_id` FOREIGN KEY (`case_id`) REFERENCES `ui_case` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `ui_result_project_id_3c6a4343_fk_project_id` FOREIGN KEY (`project_id`) REFERENCES `project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `ui_result_test_obj_id_f23df624_fk_test_obj_id` FOREIGN KEY (`test_obj_id`) REFERENCES `test_obj` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 1
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of ui_result
-- ----------------------------

-- ----------------------------
-- Table structure for ui_run_sort
-- ----------------------------
DROP TABLE IF EXISTS `ui_run_sort`;
CREATE TABLE `ui_run_sort`
(
    `id`            bigint                                                         NOT NULL AUTO_INCREMENT,
    `create_time`   datetime(6)                                                    NOT NULL,
    `update_time`   datetime(6)                                                    NOT NULL,
    `ope_type`      varchar(1048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `ass_type`      varchar(1048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `ope_value`     varchar(1048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `ope_value_key` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci   NULL DEFAULT NULL,
    `ass_value`     varchar(1048) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `run_sort`      int                                                            NULL DEFAULT NULL,
    `case_id`       bigint                                                         NULL DEFAULT NULL,
    `el_name_id`    bigint                                                         NULL DEFAULT NULL,
    `el_name_b_id`  bigint                                                         NULL DEFAULT NULL,
    `el_page_id`    bigint                                                         NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `ui_run_sort_case_id_9e28dcf2_fk_ui_case_id` (`case_id` ASC) USING BTREE,
    INDEX `ui_run_sort_el_name_id_25792dec_fk_ui_ele_id` (`el_name_id` ASC) USING BTREE,
    INDEX `ui_run_sort_el_name_b_id_55b45f3d_fk_ui_ele_id` (`el_name_b_id` ASC) USING BTREE,
    INDEX `ui_run_sort_el_page_id_7de2b5ba_fk_ui_page_id` (`el_page_id` ASC) USING BTREE,
    CONSTRAINT `ui_run_sort_case_id_9e28dcf2_fk_ui_case_id` FOREIGN KEY (`case_id`) REFERENCES `ui_case` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `ui_run_sort_el_name_b_id_55b45f3d_fk_ui_ele_id` FOREIGN KEY (`el_name_b_id`) REFERENCES `ui_ele` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `ui_run_sort_el_name_id_25792dec_fk_ui_ele_id` FOREIGN KEY (`el_name_id`) REFERENCES `ui_ele` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT `ui_run_sort_el_page_id_7de2b5ba_fk_ui_page_id` FOREIGN KEY (`el_page_id`) REFERENCES `ui_page` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 118
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of ui_run_sort
-- ----------------------------
INSERT INTO `ui_run_sort`
VALUES (5, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"test\"}', NULL, NULL, 2, 1, 1, NULL, 1);
INSERT INTO `ui_run_sort`
VALUES (6, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"123456\"}', NULL, NULL, 3, 1, 2, NULL, 1);
INSERT INTO `ui_run_sort`
VALUES (7, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 4, 1, 3, NULL, 1);
INSERT INTO `ui_run_sort`
VALUES (8, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 5, 1, 45, NULL, 1);
INSERT INTO `ui_run_sort`
VALUES (9, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 6, 1, 46, NULL, 1);
INSERT INTO `ui_run_sort`
VALUES (10, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 7, 1, 48, NULL, 1);
INSERT INTO `ui_run_sort`
VALUES (12, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 0, 2, 9, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (13, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 1, 2, 10, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (14, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 2, 2, 11, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (15, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 3, 2, 12, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (16, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 4, 2, 13, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (17, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 5, 2, 14, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (18, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 6, 2, 15, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (19, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 7, 2, 16, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (20, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 8, 2, 17, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (21, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"goods_name()\"}', 'spu_name', NULL, 10, 2, 18, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (22, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"random_100_999()\"}', NULL, NULL, 11, 2, 19, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (23, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 12, 2, 20, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (24, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 13, 2, 21, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (25, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 14, 2, 22, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (26, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"1\"}', NULL, NULL, 16, 2, 23, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (27, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"1\"}', NULL, NULL, 17, 2, 24, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (28, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"1000\"}', NULL, NULL, 18, 2, 25, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (29, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"time_random()\"}', NULL, NULL, 19, 2, 26, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (30, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 20, 2, 27, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (35, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 9, 2, 30, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (36, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 15, 2, 31, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (41, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 2, 4, 75, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (49, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_input', NULL,
        '{\"locating\":\"\",\"text\":\"卓尔数科常规生产\"}', NULL, NULL, 3, 4, 76, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (50, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 4, 4, 77, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (51, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 9, 4, 79, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (52, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 6, 4, 80, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (53, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 7, 4, 81, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (54, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 8, 4, 82, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (55, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 9, 4, 78, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (57, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"goods_name()\"}', 'spu_name', NULL, 21, 2, 65, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (58, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 22, 2, 66, NULL, 4);
INSERT INTO `ui_run_sort`
VALUES (60, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"729164035@qq.com\"}', NULL, NULL, 3, 5, 111, NULL, 13);
INSERT INTO `ui_run_sort`
VALUES (61, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"7vkhj1\"}', NULL, NULL, 3, 5, 112, NULL, 13);
INSERT INTO `ui_run_sort`
VALUES (62, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 3, 5, 113, NULL, 13);
INSERT INTO `ui_run_sort`
VALUES (67, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 1, 6, 114, NULL, 14);
INSERT INTO `ui_run_sort`
VALUES (68, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 2, 6, 125, NULL, 14);
INSERT INTO `ui_run_sort`
VALUES (69, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 3, 6, 115, NULL, 14);
INSERT INTO `ui_run_sort`
VALUES (70, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"自动化测试deasde\"}', NULL, NULL, 4, 6, 116, NULL, 14);
INSERT INTO `ui_run_sort`
VALUES (71, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 5, 6, 117, NULL, 14);
INSERT INTO `ui_run_sort`
VALUES (72, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 6, 6, 118, NULL, 14);
INSERT INTO `ui_run_sort`
VALUES (73, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 7, 6, 119, NULL, 14);
INSERT INTO `ui_run_sort`
VALUES (87, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 1, 3, 131, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (88, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 2, 3, 132, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (89, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 3, 3, 133, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (90, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 4, 3, 134, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (91, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 5, 3, 135, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (92, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 6, 3, 136, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (93, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 7, 3, 137, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (94, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 8, 3, 138, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (95, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'a_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 9, 3, 139, NULL, 9);
INSERT INTO `ui_run_sort`
VALUES (96, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"system\"}', NULL, NULL, 0, 9, 1, NULL, 1);
INSERT INTO `ui_run_sort`
VALUES (97, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"123456\"}', NULL, NULL, 1, 9, 2, NULL, 1);
INSERT INTO `ui_run_sort`
VALUES (98, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 2, 9, 3, NULL, 1);
INSERT INTO `ui_run_sort`
VALUES (99, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 3, 9, 45, NULL, 1);
INSERT INTO `ui_run_sort`
VALUES (100, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 4, 9, 141, NULL, 1);
INSERT INTO `ui_run_sort`
VALUES (101, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 5, 9, 48, NULL, 1);
INSERT INTO `ui_run_sort`
VALUES (102, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 1, 10, 144, NULL, 49);
INSERT INTO `ui_run_sort`
VALUES (103, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_get_text', NULL,
        '{\"locating\":\"\",\"set_cache_key\":\"Amount\"}', NULL, NULL, 2, 10, 143, NULL, 49);
INSERT INTO `ui_run_sort`
VALUES (105, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"maopeng@zalldigital.com\"}', NULL, NULL, 0, 11, 111, NULL, 13);
INSERT INTO `ui_run_sort`
VALUES (106, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_input', NULL,
        '{\"locating\":\"\",\"input_value\":\"maopeng123\"}', NULL, NULL, 1, 11, 112, NULL, 13);
INSERT INTO `ui_run_sort`
VALUES (107, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 2, 11, 113, NULL, 13);
INSERT INTO `ui_run_sort`
VALUES (108, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 0, 12, 122, NULL, 48);
INSERT INTO `ui_run_sort`
VALUES (109, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 1, 12, 124, NULL, 48);
INSERT INTO `ui_run_sort`
VALUES (110, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 2, 12, 146, NULL, 48);
INSERT INTO `ui_run_sort`
VALUES (112, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 4, 12, 148, NULL, 48);
INSERT INTO `ui_run_sort`
VALUES (113, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_hover', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 5, 12, 153, NULL, 48);
INSERT INTO `ui_run_sort`
VALUES (115, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_hover', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 7, 12, 150, NULL, 48);
INSERT INTO `ui_run_sort`
VALUES (116, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click_right_coordinate', NULL,
        '{\"locating\":\"\"}', NULL, NULL, 8, 12, 150, NULL, 48);
INSERT INTO `ui_run_sort`
VALUES (117, '2023-07-13 13:05:33.000000', '2023-07-13 13:05:33.000000', 'w_click', NULL, '{\"locating\":\"\"}', NULL,
        NULL, 9, 12, 152, NULL, 48);

-- ----------------------------
-- Table structure for user
-- ----------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user`
(
    `id`            bigint                                                       NOT NULL AUTO_INCREMENT,
    `create_time`   datetime(6)                                                  NOT NULL,
    `update_time`   datetime(6)                                                  NOT NULL,
    `nickname`      varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `username`      varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `password`      varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `ip`            varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `lastLoginTime` time(6)                                                      NULL DEFAULT NULL,
    `mailbox`       varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
    `role_id`       bigint                                                       NULL DEFAULT NULL,
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `user_role_id_c3a87a3d_fk_role_id` (`role_id` ASC) USING BTREE,
    CONSTRAINT `user_role_id_c3a87a3d_fk_role_id` FOREIGN KEY (`role_id`) REFERENCES `role` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB
  AUTO_INCREMENT = 12
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_0900_ai_ci
  ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of user
-- ----------------------------
INSERT INTO `user`
VALUES (1, '2023-07-13 12:45:09.000000', '2023-07-14 10:26:37.377198', '毛鹏', '18071710220', '729164035',
        '127.0.0.1:57329', '12:29:44.000000', 'maopeng@zalldigital.com', 1);
INSERT INTO `user`
VALUES (2, '2023-07-13 12:45:09.000000', '2023-07-13 12:45:09.000000', '毛鹏-小号', '17798339533', '123456',
        '127.0.0.1:52528', NULL, NULL, 2);
INSERT INTO `user`
VALUES (3, '2023-07-13 12:45:09.000000', '2023-07-13 12:45:09.000000', '吴强', '13720349413', '123456', NULL,
        '12:34:21.000000', 'wuqiang@zalldigital.com', 3);
INSERT INTO `user`
VALUES (4, '2023-07-13 12:45:09.000000', '2023-07-13 12:45:09.000000', '肖瑶', '13971463801', '123456', NULL,
        '12:45:00.000000', 'xiaoyao@zalldigital.com', 2);
INSERT INTO `user`
VALUES (5, '2023-07-13 12:45:09.000000', '2023-07-13 12:45:09.000000', '宋珊', '15871811914', '123456', NULL,
        '12:45:45.000000', 'songshan@zalldigital.com', 2);
INSERT INTO `user`
VALUES (6, '2023-07-13 12:45:09.000000', '2023-07-13 12:45:09.000000', '唐真', '13720286452', '123456', NULL,
        '12:46:43.000000', 'tangzhen@zalldigital.com', 2);
INSERT INTO `user`
VALUES (7, '2023-07-13 12:45:09.000000', '2023-07-13 12:45:09.000000', '李元', '17720581732', '123456', NULL,
        '12:47:11.000000', 'liyuan@zalldigital.com', 2);
INSERT INTO `user`
VALUES (8, '2023-07-13 12:45:09.000000', '2023-07-13 12:45:09.000000', '公用执行器', 'admin', 'admin', '127.0.0.1:2329',
        '10:21:06.000000', NULL, NULL);
INSERT INTO `user`
VALUES (11, '2023-07-13 12:45:09.000000', '2023-07-13 12:45:09.000000', '测试大大', '12312312', '12312312', NULL, NULL,
        NULL, 5);

SET
    FOREIGN_KEY_CHECKS = 1;
