# MySQL 导出与一键建库操作指南

> 用途：产出指导老师要求的数据库交付物（**能一键建库的脚本** + **数据字典 Excel**），并支撑评审现场演示正向工程。
> 编制：丘宇乾　日期：2026-09-15　环境：本机 MySQL 8.0.42 / Windows
>
> **只想打开项目数据库看数据？直接跳到第八节。**

---

## 一、老师要的是什么

| 要求（2026-09-15 语音） | 对应交付物 |
|---|---|
| "要求有你创建好的数据库〔脚本〕" | 可执行的一键建库 `.sql`（本目录 `导出_kangyang_建库脚本.sql`、`schema.sql`） |
| "还有对应的这个 Excel 文档" | 数据字典 `数据字典_康养系统_v1.0.xlsx`（16 页签） |
| "设计完了之后就能一键导出，通过它直接创建这个数据库" | 建模工具的正向工程能力（本机用 **MySQL Workbench**，见第四节） |

命令里统一用到的 MySQL 程序目录（本机未加入 PATH，所以写全路径）：

```
C:\Program Files\MySQL\MySQL Server 8.0\bin\
  ├─ mysql.exe        执行 SQL / 导入
  └─ mysqldump.exe    导出
```

> 每次执行都建议带 `--default-character-set=utf8mb4`，否则中文注释会乱码。

---

## 二、方式一：命令行 mysqldump（最稳，可脚本化）

### 2.1 导出「建库脚本」（只要结构，不要数据）

```bash
mysqldump -uroot -p123456 --default-character-set=utf8mb4 \
  --databases kangyang \
  --no-data --routines --triggers \
  --result-file="导出_kangyang_建库脚本.sql"
```

- `--databases kangyang`：让脚本自带 `CREATE DATABASE` + `USE`，**自包含**，换台机器也能直接建库
- `--no-data`：只导结构（表、索引、外键、注释）
- `--routines --triggers`：连存储过程与触发器一起导（本项目暂未使用，但建议保留）

### 2.2 导出「完整备份」（结构 + 数据）

```bash
mysqldump -uroot -p123456 --default-character-set=utf8mb4 \
  --databases kangyang \
  --single-transaction --routines --triggers --events \
  --result-file="导出_kangyang_完整备份.sql"
```

`--single-transaction` 对 InnoDB 做一致性快照，**不锁表**，适合演示环境边用边备份。

### 2.3 一键建库（把脚本灌回数据库）

```bash
mysql -uroot -p123456 --default-character-set=utf8mb4 < 导出_kangyang_建库脚本.sql
```

### 2.4 常用参数速查

| 参数 | 作用 | 什么时候用 |
|---|---|---|
| `--databases 库名` | 脚本自带建库与 `USE`，自包含 | 交交付物给老师时**必加** |
| `--no-data` | 只导结构 | 交"建库脚本" |
| `--no-create-info` | 只导数据 | 单独补数据 |
| `--single-transaction` | InnoDB 一致性快照，不锁表 | 导数据时都加 |
| `--skip-add-drop-table` | **不写 `DROP TABLE IF EXISTS`** | 只想补结构、不想清数据时（很关键，见 2.5） |
| `--where="id<=100"` | 只导部分行 | 导出小样本给老师看 |
| `--result-file=xx.sql` | 由 mysqldump 自己写文件 | Windows 下比 `>` 重定向更稳（避免 UTF-16 编码坑） |

### 2.5 实测踩到的坑（务必注意）

**mysqldump 生成的脚本默认带 `DROP TABLE IF EXISTS`，直接执行会先删表再重建 —— 数据会被清空。**

本次实测：执行 `导出_kangyang_建库脚本.sql` 后，`kangyang` 库的 12 条阈值配置与 4 个演示账号被清空（因为那是结构脚本，不带数据）。

因此固定动作是：

1. **先导完整备份**，再动结构脚本；
2. 只想补表结构而不动数据 → 加 `--skip-add-drop-table`；
3. 演示环境无所谓的话，按 `完整备份.sql` 一步还原即可。

本次已用此前导出的完整备份还原，核对结果：15 张表 / 12 条阈值 / 4 个用户 / 1 份档案 / 7 条指标 / 1 条预警，与清空前一致。

---

## 三、方式二：图形化（Workbench / Navicat 通用）

### 3.1 MySQL Workbench（本机已装 8.0 CE）

程序位置：`C:\Program Files\MySQL\MySQL Workbench 8.0\MySQLWorkbench.exe`

| 想做什么 | 菜单路径 |
|---|---|
| 导出建库脚本 / 备份 | `Server → Data Export` → 选 `kangyang` → 勾 `Dump Structure Only` 或 `Dump Structure and Data` → 选 `Export to Self-Contained File` → 设文件名 → `Start Export` |
| 一键建库 / 还原 | `Server → Data Import` → `Import from Self-Contained File` → 选 `.sql` → 选目标 schema → `Start Import` |
| 一键建库（正向工程，老师要的那个） | 打开 EER 模型 → 画/看模型 → `Database → Forward Engineer...` → 一路 Next → 生成 DDL 并**直接执行建库** |
| 从已有库反推模型 | `Database → Reverse Engineer...`（连上库 → 自动生成 EER 图） |

> 用 Workbench 画的模型可存成 `.mwb`；老师提的那款老软件（PowerDesigner）本机只剩注册表残留、程序已不在，**用 Workbench 代替即可**，它的正向工程能力完全满足"一键导出 / 直接创建数据库"。

### 3.2 导出查询结果为 Excel（做数据字典用）

在 Workbench 里跑完第四节任一查询 → 结果网格右上角点 **Export** 图标 → 选 CSV / Excel → 存盘。

---

## 四、数据字典 Excel 从哪来（两种路子）

### 4.1 路子 A：从建表脚本解析（本项目当前用法）

```bash
cd 03.概要设计/_gen
python build_dict.py      # 解析 04.编码/数据库/schema.sql → 数据字典_康养系统_v1.0.xlsx
```

优点：与 `schema.sql` **同源**，改字段只改脚本再重跑，不会出现"文档与代码不一致"。

### 4.2 路子 B：直接用 SQL 从数据库里查（"用 MySQL 导出数据字典"）

**字段清单**（数据字典的主体）：

```sql
SELECT TABLE_NAME          AS 表名,
       ORDINAL_POSITION    AS 序号,
       COLUMN_NAME         AS 字段名,
       COLUMN_TYPE         AS 类型,
       IS_NULLABLE         AS 可空,
       COLUMN_DEFAULT      AS 默认值,
       COLUMN_KEY          AS 键,
       COLUMN_COMMENT      AS 描述
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'kangyang'
ORDER BY TABLE_NAME, ORDINAL_POSITION;
```

**外键关系**（对应老师样例里"左 / 右"两列）：

```sql
SELECT TABLE_NAME            AS 左表,
       COLUMN_NAME           AS 左字段,
       REFERENCED_TABLE_NAME AS 右表,
       REFERENCED_COLUMN_NAME AS 右字段
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'kangyang'
  AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME;
```

**表清单与表注释**：

```sql
SELECT TABLE_NAME, TABLE_COMMENT, ENGINE, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'kangyang'
ORDER BY TABLE_NAME;
```

命令行直接导出成文件：

```bash
mysql -uroot -p123456 --default-character-set=utf8mb4 --batch --raw \
  -e "SELECT ... FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='kangyang';" \
  > 字段清单.tsv
```

> 两条路子的结果应一致。若不一致，说明数据库与建表脚本已经脱节，需先同步。

---

## 五、评审现场 1 分钟演示脚本（可直接照念）

1. 打开 MySQL Workbench，连上本地实例 → 左侧 schema 树展开 `kangyang`，**15 张表**一览；
2. 打开 EER 模型（或 `Reverse Engineer` 现场生成）→ 指着图说：这是 15 张表的实体关系，共 **12 个主外键**，基础表 `user` / `elder_profile` 在上层，业务表在下层；
3. `Database → Forward Engineer` → 自动生成 DDL 并执行 → 提示建库成功（**这就是"一键创建数据库"**）；
4. `Server → Data Export` → 导出结构脚本，说明这就是交付的建库脚本；
5. 打开 `数据字典_康养系统_v1.0.xlsx` → 演示"一表一页签、含类型 / 非空 / 默认值 / 左表右表外键"；
6. 收尾一句：**建库脚本、数据字典、E-R 模型三者同源，改一处即可重出另外两份。**

---

## 六、本目录文件说明与执行顺序

| 文件 | 说明 |
|---|---|
| `schema.sql` | 手写建库脚本：建库 + 15 张表 + 索引 + 12 个外键（用 `ALTER` 后置补） |
| `init_data.sql` | 初始化数据：预置管理员、6 类阈值共 12 条、演示数据 |
| `导出_kangyang_建库脚本.sql` | mysqldump 导出的结构脚本，自包含（1 建库 + 15 表 + 18 处外键 + 0 数据） |
| `导出_kangyang_完整备份.sql` | mysqldump 导出的结构 + 数据（8 张表带数据） |
| `数据字典_康养系统_v1.0.xlsx` | 16 个页签 = 说明页 + 15 张表 |

**空库一键建库（两种都可）：**

```bash
# 方式 1：走手写脚本（推荐，顺序与注释清晰）
mysql -uroot -p123456 --default-character-set=utf8mb4 < schema.sql
mysql -uroot -p123456 --default-character-set=utf8mb4 kangyang < init_data.sql

# 方式 2：走 mysqldump 备份（一步到位，含数据）
mysql -uroot -p123456 --default-character-set=utf8mb4 < 导出_kangyang_完整备份.sql
```

---

## 七、实测记录（2026-09-15）

| 项 | 结果 |
|---|---|
| 结构脚本导出 | `导出_kangyang_建库脚本.sql` 23.9 KB：1 个 `CREATE DATABASE` + 15 个 `CREATE TABLE` + 18 处 `FOREIGN KEY` + 0 条数据 |
| 完整备份导出 | `导出_kangyang_完整备份.sql` 32.1 KB：15 表 + 8 张表带数据（含阈值配置） |
| 一键建库实测 | 执行结构脚本 → 15 张表全部重建成功 |
| 副作用与还原 | 结构脚本内含 `DROP TABLE`，执行后数据被清空（`sys_config` 12 → 0）；用完整备份还原，核对恢复为 15 表 / 12 阈值 / 4 用户 / 1 档案 / 7 指标 / 1 预警 |
| 数据字典字段查询 | `information_schema.COLUMNS` 查询正常，12 个字段的名称 / 类型 / 可空 / 默认值 / 键 / 注释全部可读 |

---

## 八、附：怎么用 MySQL 打开本项目的数据库（连接与查看）

### 8.1 连接参数（本机实测）

| 项 | 值 |
|---|---|
| 主机 | `localhost`（或 `127.0.0.1`） |
| 端口 | `3306` |
| 账号 | `root` |
| 密码 | `123456` |
| **库名** | **`kangyang`** |
| MySQL 版本 | 8.0.42 Community Server |
| 服务端字符集 | `utf8mb4`（`kangyang` 库为 `utf8mb4` / `utf8mb4_general_ci`） |
| 主机名 / 数据目录 | `Murphy` / `C:\ProgramData\MySQL\MySQL Server 8.0\Data\` |
| 客户端程序 | `C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe` |

> 同实例下还有 `application`、`runoob`、`sakila`、`volunteer_application`、`world` 等库，那是别的作业/示例，**本项目只看 `kangyang`**。

### 8.2 命令行打开（最快）

```bash
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -uroot -p123456 \
  --default-character-set=utf8mb4 kangyang
```

末尾那个 `kangyang` 就是"连上后直接进这个库"。进去之后常用命令：

| 命令 | 作用 |
|---|---|
| `SHOW TABLES;` | 列出 15 张表 |
| `DESC health_warning;` | 看某张表的字段、类型、默认值 |
| `SHOW CREATE TABLE health_warning\G` | 看完整建表语句（含外键、注释），`\G` 让结果竖排更好读 |
| `SELECT * FROM user;` | 看数据 |
| `SELECT COUNT(*) FROM health_record;` | 数一下有多少条 |
| `SOURCE D:/Desktop/康养系统实训项目/04.编码/数据库/schema.sql;` | 在交互式里直接执行脚本文件 |
| `EXIT;` | 退出 |

**不进入交互式**（一条命令查完就退，适合写进脚本）：

```bash
mysql -uroot -p123456 --default-character-set=utf8mb4 kangyang -e "SELECT COUNT(*) FROM health_record;"
```

两个小技巧：加 `--table`（简写 `-t`）让输出带表格边框；语句末尾用 `\G` 代替 `;`，宽表会竖着显示。

### 8.3 Workbench 图形化打开（不熟命令行的同学用这个）

1. 启动 `C:\Program Files\MySQL\MySQL Workbench 8.0\MySQLWorkbench.exe`
2. 首页 **MySQL Connections** 右边点 `+`，新建连接：
   - Connection Name：`康养系统-本地`
   - Hostname `127.0.0.1`　Port `3306`
   - Username `root` → 点 **Store in Vault** 输密码 `123456`
   - Default Schema：`kangyang`（填了就连上直接进项目库）
   - 点 **Test Connection**，出现 Successfully made the MySQL connection 就 OK
3. 双击该连接进入 → 左侧 **SCHEMAS** 面板展开 `kangyang` → **Tables** 下面就是 15 张表
4. 看数据：在表名上右键 → `Select Rows - Limit 1000`；或开查询窗口写 SQL，点闪电图标执行
5. 看 E-R 图：菜单 `Database → Reverse Engineer...` → 选 `kangyang` → 一路 Next，自动生成实体关系图

### 8.4 打开后应该看到什么（本机实测）

```sql
SELECT 'user' AS 表名, COUNT(*) FROM user
UNION ALL SELECT 'elder_profile', COUNT(*) FROM elder_profile
UNION ALL SELECT 'health_record', COUNT(*) FROM health_record
UNION ALL SELECT 'health_warning', COUNT(*) FROM health_warning
UNION ALL SELECT 'sys_config', COUNT(*) FROM sys_config;
```

| 表 | 行数 |
|---|---|
| `user` | 4 |
| `elder_profile` | 1 |
| `health_record` | 7 |
| `health_warning` | 1 |
| `sys_config` | 12 |

演示账号（密码统一 `Abc123456`）：

| 手机号 | 姓名 | 角色 |
|---|---|---|
| 13000000001 | 系统管理员 | ADMIN |
| 13000000002 | 张桂兰 | ELDER |
| 13000000003 | 李强 | FAMILY |
| 13000000004 | 王护工 | CARE |

阈值配置示例（`sys_config` 中 `group_name='threshold'` 的条目，前端正常范围就取自这里）：

| 配置键 | 值 |
|---|---|
| `BLOOD_PRESSURE_SYSTOLIC` | `{"level0":"90~139","level1":"140~159","level2":"160~179","level3":">=180"}` |
| `BLOOD_PRESSURE_DIASTOLIC` | `{"level0":"60~89","level1":"90~99","level2":"100~109","level3":">=110"}` |
| `BLOOD_SUGAR` | `{"level0":"3.9~6.1","level1":"6.2~7.0","level2":"7.1~11.1","level3":">=11.2"}` |

### 8.5 常见问题

| 现象 | 原因与处理 |
|---|---|
| `'mysql' 不是内部或外部命令` | MySQL 的 bin 目录没加入 PATH → 用全路径，或把 `C:\Program Files\MySQL\MySQL Server 8.0\bin` 加进系统 PATH |
| `Access denied for user 'root'@'localhost'` | 密码不对，本机是 `123456` |
| `Can't connect to MySQL server on 'localhost:3306'` | MySQL 服务没启动 → 在"服务"（`services.msc`）里找 MySQL 开头的服务启动它 |
| 中文显示成 `???` 或乱码 | 命令漏了 `--default-character-set=utf8mb4`；已连上的会话可执行 `SET NAMES utf8mb4;` 补救 |
| 提示 `Using a password on the command line interface can be insecure` | 只是安全提示，不影响执行；介意就把 `-p123456` 改成 `-p`，回车后再输密码 |
| 输出表格错位 | 加 `--table` 参数；或把语句结尾改成 `\G` 竖排 |
