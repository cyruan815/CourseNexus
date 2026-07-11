# 操作系统第十二章真实模型学习计划测试报告

- 测试日期：2026-07-12
- 自然语言输入：我要两天学完操作系统这门课的第十二章
- PDF：`D:\大二下课程\操作系统\课件\第12章 保护和安全3课时.pdf`
- 说明：密钥只用于本次模型调用，报告不记录密钥值。

## 模型配置摘要

```json
{
  "env": {
    "STUDY_PLAN_PARSER_API_KEY": {
      "configured": true,
      "source": ".env.example"
    },
    "STUDY_PLAN_PARSER_BASE_URL": {
      "configured": true,
      "source": ".env.example"
    },
    "STUDY_PLAN_PARSER_MODEL": {
      "configured": true,
      "source": ".env.example"
    },
    "STUDY_PLAN_GENERATOR_API_KEY": {
      "configured": true,
      "source": ".env.example"
    },
    "STUDY_PLAN_GENERATOR_BASE_URL": {
      "configured": true,
      "source": ".env.example"
    },
    "STUDY_PLAN_GENERATOR_MODEL": {
      "configured": true,
      "source": ".env.example"
    }
  },
  "parser_endpoint": {
    "purpose": "study_plan_parser",
    "api_key_configured": true,
    "base_url_configured": true,
    "model": "deepseek-chat"
  },
  "generator_endpoint": {
    "purpose": "study_plan_generator",
    "api_key_configured": true,
    "base_url_configured": true,
    "model": "deepseek-chat"
  }
}
```

## 归一化后的 preview 请求

```json
{
  "goal_text": "我要两天学完操作系统这门课的第十二章",
  "start_date": "2026-07-12",
  "end_date": "2026-07-13",
  "daily_available_minutes": 180,
  "material_scope": {
    "include_all_parsed_materials": true,
    "material_ids": []
  }
}
```

## PDF 解析输出

```json
{
  "material_id": "mat_0def5fcae3d54728b4e89277a0ad1186",
  "name": "第12章 保护和安全3课时.pdf",
  "material_type": "pdf",
  "parse_status": "parsed",
  "parse_error": null,
  "chunk_count": 14,
  "chunks": [
    {
      "chunk_id": "chk_0def5fcae3d54728b4e89277a0ad1186_000000",
      "chunk_index": 0,
      "heading": null,
      "page": "2",
      "text": "第 2 章, 操作系统引论 = 进程的描述与控制. 第 3 章, 操作系统引论 = 处理机调度与死锁. 第 4 章, 操作系统引论 = 进程同步. 第 5 章, 操作系统引论 = 存储器管理. 第 6 章, 操作系统引论 = 虚拟存储器. 第 7 章, 操作系统引论 = 输入 / 输出系统. 第 8 章, 操作系统引论 = 文件管理. 第 9 章, 操作系统引论 = 磁盘存储器管理. 第 10 章, 操作系统引论 = 多处理机操作系统. 第 11 章, 操作系统引论 = 虚拟化和云计算. 第 12 章, 操作系统引论 = 保护和安全"
    },
    {
      "chunk_id": "chk_0def5fcae3d54728b4e89277a0ad1186_000001",
      "chunk_index": 1,
      "heading": "12.1 安全环境",
      "page": "3",
      "text": "12.2 数据加密技术\n12.3 用户验证\n- 12.4 来自系统内部的攻击\n- 12.5 来自系统外部的攻击\n12.6 可信系统"
    },
    {
      "chunk_id": "chk_0def5fcae3d54728b4e89277a0ad1186_000002",
      "chunk_index": 2,
      "heading": "保护可被定义为：",
      "page": "4",
      "text": "- 能够对攻击、入侵和损害系统的行为进 行防御或监视的设施"
    },
    {
      "chunk_id": "chk_0def5fcae3d54728b4e89277a0ad1186_000003",
      "chunk_index": 3,
      "heading": "安全可被定义为：",
      "page": "4",
      "text": "- 对系统完整性和数据安全性的可信度衡量\n实现'安全环境'是目标，而保护是为了实 现该目标所采取的方法和措施\nsender"
    },
    {
      "chunk_id": "chk_0def5fcae3d54728b4e89277a0ad1186_000004",
      "chunk_index": 4,
      "heading": "数据机密性",
      "page": "5",
      "text": "- 是指将机密的数据置于保密状态，仅允许被授权用户访问系统中的信息，以避免数 据暴露\n- 数据完整性\n- 是指未经授权的用户，不能擅自篡改系统中所保存的数据\n- 系统可用性\n- 是指保证计算机中的资源可供授权用户随时访问，而系统不会拒绝服务\n- 面对的三个威胁\n- 攻击者通过各种方式窃取系统中的机密信息以使其暴露\n- 攻击者擅自修改系统中所保存的数据以使其被破坏（即实现数据篡改）\n- 攻击者采用多种方法来扰乱系统以使其瘫痪而拒绝提供服务\n信息技术安全评价通用准则，简称 CC ，作为了国际标准。\n- 1983 年，美国国防部颁布了历史上第一个计算机安全评价标准，最核心 文件是 TCSEC ，因它是橙色封皮，简称'橙皮书'。"
    },
    {
      "chunk_id": "chk_0def5fcae3d54728b4e89277a0ad1186_000005",
      "chunk_index": 5,
      "heading": "计算机安全的分类：",
      "page": "6",
      "text": "- TCSEC 将计算机系统的安全程度划分为 4 类： D 、 C 、 B 、 A 。\n- 共分为 7 个等级： D 、 C1 、 C2 、 B1 、 B2 、 B3 、 A1 。\n- ① D 类，最低安全类别，又称为安全保护欠缺级。凡是无法达到另外 3 类标准 要求的，都被归为 D 类。 MS-DOS 属于 D 类。\n- ② C1 级。 C 类是仅高于 D 类的安全类别。 C 类分为两级： C1 和 C2 。 C1 级要求 OS 使用保护模式和用户登录验证，并赋予用户自主访问控制权，即允许用 户指定其他用户对自己文件的使用权限。大部分的 UNIX 系统属于 C1 级。\n- ③ C2 级，称为受控存取控制级。它是在 C1 级的基础上，增加了一个个体层访问控 制。当前广泛使用的安全软件大多属于 C2 级。\n- ④ B1 级，具有 C2 级的全部安全属性。在 B 类系统中，会为每个可控用户和对象贴 上一个安全标注。\n- ⑤ B2 级，具有 B1 级的全部安全属性。 B2 级要求系统必须采用自上而下的结构化设 计方法，并能够对设计方法进行检验，对可能存在的隐蔽信道进行安全分析。\n- ⑥ B3 级，具有 B2 级的全部安全属性。在 B3 级系统中必须包含用户和组的访问控制 表、足够的安全审计和灾难恢复能力。\n- ⑦ A1 级，要求系统具有强制存取控制和形式化模型技术的应用，能证明模型是正 确的，并须说明有关实现方法是与保护模型一致的。\n12.1 安全环境\n12.2\n数据加密技术\n12.3 用户验证\n- 12.4 来自系统内部的攻击\n- 12.5 来自系统外部的攻击\n12.6 可信系统"
    },
    {
      "chunk_id": "chk_0def5fcae3d54728b4e89277a0ad1186_000006",
      "chunk_index": 6,
      "heading": "第 12 章保护和安全",
      "page": "9",
      "text": "加密是一种密写科学， 用于把系统中的数据 ( 称为明文 ) 转换为密文。 使攻击者即使截获到被 加密的数据，也无法了 解数据的内容，从而有 效地保护了系统中信息 的安全性"
    },
    {
      "chunk_id": "chk_0def5fcae3d54728b4e89277a0ad1186_000007",
      "chunk_index": 7,
      "heading": "数据加密技术包括：",
      "page": "9",
      "text": "- 数据加密\n- 数据解密\n- 数字签名\n- 签名识别\n- 数字证明\n➢\n…"
    },
    {
      "chunk_id": "chk_0def5fcae3d54728b4e89277a0ad1186_000008",
      "chunk_index": 8,
      "heading": "数据加密模型由 4 部分组成",
      "page": "10",
      "text": "- ① 明文：被加密的文 本，称为明文 P 。\n02\n- ① 密文：加密后 的文本，称为 密文 Y 。\n03\n- ① 加密（解密）算法 EKe （ DKd ）：用于 实现从明文（密文） 到密文（明文）转换 的公式、规则或程序。\n04\n- ① 密钥 K ：加密和 解密算法中的 关键参数。\n-  设计密码技术称为 密 码编码\n- \n- 将破译密码技术称为 密码分析\n-  密码编码和密码分析 合起来称为 密码学"
    },
    {
      "chunk_id": "chk_0def5fcae3d54728b4e89277a0ad1186_000009",
      "chunk_index": 9,
      "heading": "基本加密方法 -易位法",
      "page": "12",
      "text": "- 易位法是指按照一定的规则，重新安排明文中的比特或字符的顺序以形成密 文，而字符本身却保持不变。\n- 按易位单位的不同，易位法又可分\n- 成比特易位和字符易位两种\n- 比特易位法简单易行，并可用硬件 实现，主要用于数字通信中\n- 字符易位法利用密钥对明文进行易 位后形成密文\nM\nE, 1 = G. E, 2 = . E, 3 = . E, 4 = B. E, 5 = U. E, 6 = C. E, 7 = K. 7, 1 = 4. 7, 2 = 7. 7, 3 = 1 2. 7, 4 = 8. 7, 5 = 3. 7, 6 = . 7, 7 = 6. p 1, 1 = e. p 1, 2 = . p 1, 3 = a. p 1, 4 = S. p 1, 5 = e. p 1, 6 = t. p 1, 7 = r. a n, 1 = S. a n, 2 = . a n, 3 = f. a n, 4 = e. a n, 5 = r. a n, 6 = 0. a n, 7 = n. e, 1 = m. e, 2 = i. e, 3 = 1 1. e, 4 = i. e, 5 = . e, 6 = 0. e, 7 = n. d 0, 1 = 1. d 0, 2 = 1. d 0, 3 = a. d 0, 4 = r. d 0, 5 = . d 0, 6 = S. d 0, 7 = t. 0 m, 1 = y. 0 m, 2 = S. 0 m, 3 = W. 0 m, 4 = i. 0 m, 5 = . 0 m, 6 = S. 0 m, 7 = S. b a, 1 = n. b a, 2 = k. b a, 3 = a. b a, 4 = c. b a, 5 = . b a, 6 = c. b a, 7 = 0. u n, 1 = t. u n, 2 = S. u n, 3 = i. u n, 4 = X. u n, 5 = . u n, 6 = t. u n, 7 = W. 0 t, 1 = W. 0 t, 2 = . 0 t, 3 = a. 0 t, 4 = b. 0 t, 5 = . 0 t, 6 = c. 0 t, 7 = d"
    },
    {
      "chunk_id": "chk_0def5fcae3d54728b4e89277a0ad1186_000010",
      "chunk_index": 10,
      "heading": "明文",
      "page": "12",
      "text": "Please transfer one million dollars to my Swiss Bank account six two two …"
    },
    {
      "chunk_id": "chk_0def5fcae3d54728b4e89277a0ad1186_000011",
      "chunk_index": 11,
      "heading": "密文",
      "page": "12",
      "text": "AFLLSKSOSELAWAIA TOOSSCTCLNMOMANT ESIL YNTWRNNTSOWD FAEDOBNO ·\n置换法是指按照一定的规则， 用一个字符去置换（替代）另 一个字符以形成密文\n这种密码很容易被破译\nX\n例如，将 26 个英文字母通过密钥 QWERTYUIOPASDFGHJKLZX CVBNM 映像到另外 26 个特定字 母中，利用置换法和密钥，可将 attack 加密而使其变为 QZZQEA ，\nX\nhttp s ://www.baidu.com http s ://cn.bing.com"
    },
    {
      "chunk_id": "chk_0def5fcae3d54728b4e89277a0ad1186_000012",
      "chunk_index": 12,
      "heading": "面试： HTTPS 中' S '代表？",
      "page": "14",
      "text": "很多人会回答 HTTPS 是一个网络协议，其实严格来讲， HTTPS 并不是某种网络协议，而是 HTTP + SSL 组成的'以安全为目标的 HTTP 通道'。"
    },
    {
      "chunk_id": "chk_0def5fcae3d54728b4e89277a0ad1186_000013",
      "chunk_index": 13,
      "heading": "面试： HTTPS 是如何加密的？",
      "page": "14",
      "text": "说到 HTTPS 的加密过程，就不得不提一下加密方式的分类，主要分为 对称加密 与 非对称加密\n由大家都信得过的认证机构 CA 为公开密钥发放一份公开密钥证明书，该公开密 钥证明书又称为数字证明书，用于证明通信请求者的身份。\n国际电信联盟（ ITU ）制定的 X.509 标准中，规定了数字证明书的内容\n- 用户名称、发证机构名称、公开密钥、公开密钥的有效日期、数字证明书 的编号以及发证者的签名。"
    }
  ]
}
```

## 真实模型底层调用记录

```json
[
  {
    "provider": "study_plan_parser",
    "api": "responses.parse",
    "model": "deepseek-chat",
    "schema": "StudyPlanParsedConfig",
    "ok": false,
    "error_class": "NotFoundError",
    "status_code": 404
  },
  {
    "provider": "study_plan_parser",
    "api": "chat.completions.create",
    "model": "deepseek-chat",
    "response_format": {
      "type": "json_object"
    },
    "ok": true,
    "content_excerpt": "{\n  \"goal_text\": \"我要两天学完操作系统这门课的第十二章\",\n  \"start_date\": null,\n  \"end_date\": null,\n  \"daily_available_minutes\": null,\n  \"preference\": null,\n  \"material_scope\": {\n    \"include_all_parsed_materials\": true,\n    \"material_ids\": []\n  },\n  \"unresolved_fields\": [\"start_date\", \"end_date\", \"daily_available_minutes\", \"preference\"]\n}"
  },
  {
    "provider": "study_plan_generator",
    "api": "responses.parse",
    "model": "deepseek-chat",
    "schema": "PlanBatchExtraction",
    "ok": false,
    "error_class": "NotFoundError",
    "status_code": 404
  },
  {
    "provider": "study_plan_generator",
    "api": "chat.completions.create",
    "model": "deepseek-chat",
    "response_format": {
      "type": "json_object"
    },
    "ok": true,
    "content_excerpt": "{\n  \"units\": [\n    {\n      \"topic\": \"安全环境概述\",\n      \"summary\": \"介绍保护与安全的定义、安全目标（机密性、完整性、可用性）以及计算机安全评价标准（TCSEC分级）。\",\n      \"difficulty\": \"medium\",\n      \"estimated_minutes\": 50,\n      \"related_material_ids\": [\"mat_0def5fcae3d54728b4e89277a0ad1186\"],\n      \"citation_chunk_ids\": [\"chk_0def5fcae3d54728b4e89277a0ad1186_000002\", \"chk_0def5fcae3d54728b4e89277a0ad1186_000003\", \"chk_0def5fcae3d54728b4e89277a0ad1186_000004\", \"chk_0def5fcae3d54728b4e89277a0ad1186_000005\"]\n    },\n    {\n      \"topic\": \"数据加密技术\",\n      \"summary\": \"讲解加密模型、基本加密方法（易位法和置换法）以及HTTPS中的对称与非对称加密概念。\",\n      \"difficulty\": \"hard\",\n      \"estimated_minutes\": 70,\n      \"related_material_ids\": [\"mat_0def5fcae3d54728b4e89277a0ad1186\"],\n      \"citation_chunk_ids\": [\"chk_0def5fcae3d54728b4e89277a0ad1186_000006\", \"chk_0def5fcae3d54728b4e89"
  },
  {
    "provider": "study_plan_generator",
    "api": "responses.parse",
    "model": "deepseek-chat",
    "schema": "StudyPlanReduction",
    "ok": false,
    "error_class": "NotFoundError",
    "status_code": 404
  },
  {
    "provider": "study_plan_generator",
    "api": "chat.completions.create",
    "model": "deepseek-chat",
    "response_format": {
      "type": "json_object"
    },
    "ok": true,
    "content_excerpt": "{\n  \"title\": \"两天学完操作系统第十二章\",\n  \"tasks\": [\n    {\n      \"title\": \"第一天：安全环境与加密技术\",\n      \"task_date\": \"2026-07-12\",\n      \"sort_order\": 1,\n      \"subtasks\": [\n        {\n          \"title\": \"安全环境概述\",\n          \"subtask_type\": \"learn\",\n          \"description\": \"介绍保护与安全的定义、安全目标（机密性、完整性、可用性）以及计算机安全评价标准（TCSEC分级）。\",\n          \"related_material_ids\": [\"mat_0def5fcae3d54728b4e89277a0ad1186\"],\n          \"estimated_minutes\": 50,\n          \"citation_chunk_ids\": [\"chk_0def5fcae3d54728b4e89277a0ad1186_000002\", \"chk_0def5fcae3d54728b4e89277a0ad1186_000003\", \"chk_0def5fcae3d54728b4e89277a0ad1186_000004\", \"chk_0def5fcae3d54728b4e89277a0ad1186_000005\"],\n          \"sort_order\": 1\n        },\n        {\n          \"title\": \"数据加密技术\",\n          \"subtask_type\": \"learn\",\n          \"description\": \"讲解加密模型、基本加密方法（易位法和置换法）"
  }
]
```

## 真实模型结构化输出

```json
[
  {
    "provider": "study_plan_parser",
    "schema": "StudyPlanParsedConfig",
    "prompt_excerpt": "你是 CourseNexus 的学习计划配置解析器。\n只从用户目标中提取可编辑的学习计划字段，不创建计划，不编造无法确定的信息。\n无法可靠确定的字段填 null，并把字段名加入 unresolved_fields。\n课程名称：操作系统\n用户目标：我要两天学完操作系统这门课的第十二章\n资料范围：{'include_all_parsed_materials': True, 'material_ids': []}",
    "result": {
      "goal_text": "我要两天学完操作系统这门课的第十二章",
      "start_date": null,
      "end_date": null,
      "daily_available_minutes": null,
      "preference": null,
      "material_scope": {
        "include_all_parsed_materials": true,
        "material_ids": []
      },
      "unresolved_fields": [
        "start_date",
        "end_date",
        "daily_available_minutes",
        "preference"
      ]
    }
  },
  {
    "provider": "study_plan_generator",
    "schema": "PlanBatchExtraction",
    "prompt_excerpt": "你是 CourseNexus 的学习计划材料分析器。\n请把本批资料提炼为可排入学习计划的知识单元。\ngoal_text: 我要两天学完操作系统这门课的第十二章\ndate_range: 2026-07-12 to 2026-07-13\ndaily_available_minutes: 180\nmaterial_ids: mat_0def5fcae3d54728b4e89277a0ad1186\nchunks:\nchunk_id=chk_0def5fcae3d54728b4e89277a0ad1186_000000 material_id=mat_0def5fcae3d54728b4e89277a0ad1186 heading= text=第 2 章, 操作系统引论 = 进程的描述与控制. 第 3 章, 操作系统引论 = 处理机调度与死锁. 第 4 章, 操作系统引论 = 进程同步. 第 5 章, 操作系统引论 = 存储器管理. 第 6 章, 操作系统引论 = 虚拟存储器. 第 7 章, 操作系统引论 = 输入 / 输出系统. 第 8 章, 操作系统引论 = 文件管理. 第 9 章, 操作系统引论 = 磁盘存储器管理. 第 10 章, 操作系统引论 = 多处理机操作系统. 第 11 章, 操作系统引论 = 虚拟化和云计算. 第 12 章, 操作系统引论 = 保护和安全\nchunk_id=chk_0def5fcae3d54728b4e89277a0ad1186_000001 material_id=mat_0def5fcae3d54728b4e89277a0ad1186 heading=12.1 安全环境 text=12.2 数据加密技术\n12.3 用户验证\n- 12.4 来自系统内部的攻击\n- 12.5 来自系统外部的攻击\n12.6 可信系统\nchunk_id=chk_0def5fcae3d54728b4e89277a0ad1186_000002 material_id=mat_0def5fcae3d54728b4e89277a0ad1186 heading=保护可被定义为： text=- 能够对攻击、入侵和损害系统的行为进 行防御或监视的设施\nchunk_id=chk_0def5fcae3d54728b4e89277a0ad1186_000003 material_id=mat_0def5fcae3d54728b4e89277a0ad1186 heading=安全可被定义为： text=- 对系统完整性和数据安全性的可信度衡量\n实现'安全环境'是目标，而保护是为了实 现该目标所采取的方法和措施\nsender\nchunk_id=chk_0def5fcae3d54728b4e89277a0ad1186_000004 material_id=mat_0def5fcae",
    "result": {
      "units": [
        {
          "topic": "安全环境概述",
          "summary": "介绍保护与安全的定义、安全目标（机密性、完整性、可用性）以及计算机安全评价标准（TCSEC分级）。",
          "difficulty": "medium",
          "estimated_minutes": 50,
          "related_material_ids": [
            "mat_0def5fcae3d54728b4e89277a0ad1186"
          ],
          "citation_chunk_ids": [
            "chk_0def5fcae3d54728b4e89277a0ad1186_000002",
            "chk_0def5fcae3d54728b4e89277a0ad1186_000003",
            "chk_0def5fcae3d54728b4e89277a0ad1186_000004",
            "chk_0def5fcae3d54728b4e89277a0ad1186_000005"
          ]
        },
        {
          "topic": "数据加密技术",
          "summary": "讲解加密模型、基本加密方法（易位法和置换法）以及HTTPS中的对称与非对称加密概念。",
          "difficulty": "hard",
          "estimated_minutes": 70,
          "related_material_ids": [
            "mat_0def5fcae3d54728b4e89277a0ad1186"
          ],
          "citation_chunk_ids": [
            "chk_0def5fcae3d54728b4e89277a0ad1186_000006",
            "chk_0def5fcae3d54728b4e89277a0ad1186_000007",
            "chk_0def5fcae3d54728b4e89277a0ad1186_000008",
            "chk_0def5fcae3d54728b4e89277a0ad1186_000009",
            "chk_0def5fcae3d54728b4e89277a0ad1186_000010",
            "chk_0def5fcae3d54728b4e89277a0ad1186_000011",
            "chk_0def5fcae3d54728b4e89277a0ad1186_000012",
            "chk_0def5fcae3d54728b4e89277a0ad1186_000013"
          ]
        },
        {
          "topic": "用户验证与攻击",
          "summary": "涵盖用户验证技术及来自系统内部和外部的攻击类型（如数据篡改、拒绝服务等）。",
          "difficulty": "medium",
          "estimated_minutes": 30,
          "related_material_ids": [
            "mat_0def5fcae3d54728b4e89277a0ad1186"
          ],
          "citation_chunk_ids": [
            "chk_0def5fcae3d54728b4e89277a0ad1186_000001"
          ]
        },
        {
          "topic": "可信系统",
          "summary": "介绍可信系统的概念及安全等级（B3、A1等）特征。",
          "difficulty": "easy",
          "estimated_minutes": 30,
          "related_material_ids": [
            "mat_0def5fcae3d54728b4e89277a0ad1186"
          ],
          "citation_chunk_ids": [
            "chk_0def5fcae3d54728b4e89277a0ad1186_000001"
          ]
        }
      ],
      "citation_chunk_ids": [
        "chk_0def5fcae3d54728b4e89277a0ad1186_000000",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000001",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000002",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000003",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000004",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000005",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000006",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000007",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000008",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000009",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000010",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000011",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000012",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000013"
      ]
    }
  },
  {
    "provider": "study_plan_generator",
    "schema": "StudyPlanReduction",
    "prompt_excerpt": "你是 CourseNexus 的学习计划排程器。\n请把所有材料单元归并为日期连续、可执行的单课程学习计划预览。\ngoal_text: 我要两天学完操作系统这门课的第十二章\ndate_range: 2026-07-12 to 2026-07-13\ndaily_available_minutes: 180\nexpected_material_ids: mat_0def5fcae3d54728b4e89277a0ad1186\nmapped_batches: [{'units': [{'topic': '安全环境概述', 'summary': '介绍保护与安全的定义、安全目标（机密性、完整性、可用性）以及计算机安全评价标准（TCSEC分级）。', 'difficulty': 'medium', 'estimated_minutes': 50, 'related_material_ids': ['mat_0def5fcae3d54728b4e89277a0ad1186'], 'citation_chunk_ids': ['chk_0def5fcae3d54728b4e89277a0ad1186_000002', 'chk_0def5fcae3d54728b4e89277a0ad1186_000003', 'chk_0def5fcae3d54728b4e89277a0ad1186_000004', 'chk_0def5fcae3d54728b4e89277a0ad1186_000005']}, {'topic': '数据加密技术', 'summary': '讲解加密模型、基本加密方法（易位法和置换法）以及HTTPS中的对称与非对称加密概念。', 'difficulty': 'hard', 'estimated_minutes': 70, 'related_material_ids': ['mat_0def5fcae3d54728b4e89277a0ad1186'], 'citation_chunk_ids': ['chk_0def5fcae3d54728b4e89277a0ad1186_000006', 'chk_0def5fcae3d54728b4e89277a0ad1186_000007', 'chk_0def5fcae3d54728b4e89277a0ad1186_000008', 'chk_0def5fcae3d54728b4e89277a0ad1186_000009', 'chk_0def5fcae3d54728b4e89277a0ad1186_000010', 'chk_0def5fcae3d54728b4e89277a0ad1186_000011', 'chk_0def5fcae3d54728b4e89277a0ad1186_000012', 'chk_0",
    "result": {
      "title": "两天学完操作系统第十二章",
      "tasks": [
        {
          "title": "第一天：安全环境与加密技术",
          "task_date": "2026-07-12",
          "sort_order": 1,
          "subtasks": [
            {
              "title": "安全环境概述",
              "subtask_type": "learn",
              "description": "介绍保护与安全的定义、安全目标（机密性、完整性、可用性）以及计算机安全评价标准（TCSEC分级）。",
              "related_material_ids": [
                "mat_0def5fcae3d54728b4e89277a0ad1186"
              ],
              "estimated_minutes": 50,
              "citation_chunk_ids": [
                "chk_0def5fcae3d54728b4e89277a0ad1186_000002",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000003",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000004",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000005"
              ],
              "sort_order": 1
            },
            {
              "title": "数据加密技术",
              "subtask_type": "learn",
              "description": "讲解加密模型、基本加密方法（易位法和置换法）以及HTTPS中的对称与非对称加密概念。",
              "related_material_ids": [
                "mat_0def5fcae3d54728b4e89277a0ad1186"
              ],
              "estimated_minutes": 70,
              "citation_chunk_ids": [
                "chk_0def5fcae3d54728b4e89277a0ad1186_000006",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000007",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000008",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000009",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000010",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000011",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000012",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000013"
              ],
              "sort_order": 2
            },
            {
              "title": "用户验证与攻击",
              "subtask_type": "learn",
              "description": "涵盖用户验证技术及来自系统内部和外部的攻击类型（如数据篡改、拒绝服务等）。",
              "related_material_ids": [
                "mat_0def5fcae3d54728b4e89277a0ad1186"
              ],
              "estimated_minutes": 30,
              "citation_chunk_ids": [
                "chk_0def5fcae3d54728b4e89277a0ad1186_000001"
              ],
              "sort_order": 3
            },
            {
              "title": "可信系统",
              "subtask_type": "learn",
              "description": "介绍可信系统的概念及安全等级（B3、A1等）特征。",
              "related_material_ids": [
                "mat_0def5fcae3d54728b4e89277a0ad1186"
              ],
              "estimated_minutes": 30,
              "citation_chunk_ids": [
                "chk_0def5fcae3d54728b4e89277a0ad1186_000001"
              ],
              "sort_order": 4
            }
          ]
        },
        {
          "title": "第二天：复习与测验",
          "task_date": "2026-07-13",
          "sort_order": 2,
          "subtasks": [
            {
              "title": "复习第十二章内容",
              "subtask_type": "review",
              "description": "复习安全环境、加密、用户验证、攻击类型和可信系统。",
              "related_material_ids": [
                "mat_0def5fcae3d54728b4e89277a0ad1186"
              ],
              "estimated_minutes": 60,
              "citation_chunk_ids": [
                "chk_0def5fcae3d54728b4e89277a0ad1186_000000",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000001",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000002",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000003",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000004",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000005",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000006",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000007",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000008",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000009",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000010",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000011",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000012",
                "chk_0def5fcae3d54728b4e89277a0ad1186_000013"
              ],
              "sort_order": 1
            },
            {
              "title": "章节测验",
              "subtask_type": "quiz",
              "description": "完成第十二章的测验题目。",
              "related_material_ids": [
                "mat_0def5fcae3d54728b4e89277a0ad1186"
              ],
              "estimated_minutes": 60,
              "citation_chunk_ids": [],
              "sort_order": 2
            },
            {
              "title": "综合测试",
              "subtask_type": "test",
              "description": "进行第十二章的综合测试。",
              "related_material_ids": [
                "mat_0def5fcae3d54728b4e89277a0ad1186"
              ],
              "estimated_minutes": 60,
              "citation_chunk_ids": [],
              "sort_order": 3
            }
          ]
        }
      ],
      "citation_chunk_ids": [
        "chk_0def5fcae3d54728b4e89277a0ad1186_000000",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000001",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000002",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000003",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000004",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000005",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000006",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000007",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000008",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000009",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000010",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000011",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000012",
        "chk_0def5fcae3d54728b4e89277a0ad1186_000013"
      ]
    }
  }
]
```

## 模型提炼的知识点

```json
[
  {
    "topic": "安全环境概述",
    "summary": "介绍保护与安全的定义、安全目标（机密性、完整性、可用性）以及计算机安全评价标准（TCSEC分级）。",
    "difficulty": "medium",
    "estimated_minutes": 50,
    "related_material_ids": [
      "mat_0def5fcae3d54728b4e89277a0ad1186"
    ],
    "citation_chunk_ids": [
      "chk_0def5fcae3d54728b4e89277a0ad1186_000002",
      "chk_0def5fcae3d54728b4e89277a0ad1186_000003",
      "chk_0def5fcae3d54728b4e89277a0ad1186_000004",
      "chk_0def5fcae3d54728b4e89277a0ad1186_000005"
    ]
  },
  {
    "topic": "数据加密技术",
    "summary": "讲解加密模型、基本加密方法（易位法和置换法）以及HTTPS中的对称与非对称加密概念。",
    "difficulty": "hard",
    "estimated_minutes": 70,
    "related_material_ids": [
      "mat_0def5fcae3d54728b4e89277a0ad1186"
    ],
    "citation_chunk_ids": [
      "chk_0def5fcae3d54728b4e89277a0ad1186_000006",
      "chk_0def5fcae3d54728b4e89277a0ad1186_000007",
      "chk_0def5fcae3d54728b4e89277a0ad1186_000008",
      "chk_0def5fcae3d54728b4e89277a0ad1186_000009",
      "chk_0def5fcae3d54728b4e89277a0ad1186_000010",
      "chk_0def5fcae3d54728b4e89277a0ad1186_000011",
      "chk_0def5fcae3d54728b4e89277a0ad1186_000012",
      "chk_0def5fcae3d54728b4e89277a0ad1186_000013"
    ]
  },
  {
    "topic": "用户验证与攻击",
    "summary": "涵盖用户验证技术及来自系统内部和外部的攻击类型（如数据篡改、拒绝服务等）。",
    "difficulty": "medium",
    "estimated_minutes": 30,
    "related_material_ids": [
      "mat_0def5fcae3d54728b4e89277a0ad1186"
    ],
    "citation_chunk_ids": [
      "chk_0def5fcae3d54728b4e89277a0ad1186_000001"
    ]
  },
  {
    "topic": "可信系统",
    "summary": "介绍可信系统的概念及安全等级（B3、A1等）特征。",
    "difficulty": "easy",
    "estimated_minutes": 30,
    "related_material_ids": [
      "mat_0def5fcae3d54728b4e89277a0ad1186"
    ],
    "citation_chunk_ids": [
      "chk_0def5fcae3d54728b4e89277a0ad1186_000001"
    ]
  }
]
```

## 后端 API 实际返回

```json
{
  "auth.register": {
    "status_code": 200,
    "body": {
      "data": {
        "access_token": "eyJleHAiOjE3ODM4NzQ4ODYsInN1YiI6InVzcl83MTk2YjkzNTcyOGI0ZjdkYWQ5NzhkZjM2M2U5ODljYSJ9.HJoiyHNFLeKZVGSySmsiSnFHJmBz_bb05vp4gVmyZmI",
        "token_type": "bearer",
        "expires_at": "2026-07-12T16:48:06.095803Z",
        "user": {
          "id": "usr_7196b935728b4f7dad978df363e989ca",
          "username": "os_ch12_real_model",
          "nickname": null,
          "avatar_url": null,
          "status": "active",
          "created_at": "2026-07-11T16:48:06"
        }
      },
      "meta": {
        "request_id": "req_d03ea578620440f981f3ef7a5bfb3391",
        "server_time": "2026-07-11T16:48:06.096316+00:00",
        "api_version": "v1"
      }
    }
  },
  "courses.create": {
    "status_code": 200,
    "body": {
      "data": {
        "id": "crs_c7960168afc743c58a2322dbc4453d97",
        "user_id": "usr_7196b935728b4f7dad978df363e989ca",
        "name": "操作系统",
        "description": null,
        "teacher": null,
        "term": null,
        "status": "active",
        "created_at": "2026-07-11T16:48:06",
        "updated_at": "2026-07-11T16:48:06",
        "deleted_at": null
      },
      "meta": {
        "request_id": "req_45c3dd96f5c949269c6c1ce9eb9f2c91",
        "server_time": "2026-07-11T16:48:06.114590+00:00",
        "api_version": "v1"
      }
    }
  },
  "materials.upload": {
    "status_code": 200,
    "body": {
      "data": {
        "id": "mat_0def5fcae3d54728b4e89277a0ad1186",
        "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
        "user_id": "usr_7196b935728b4f7dad978df363e989ca",
        "folder_id": null,
        "name": "第12章 保护和安全3课时.pdf",
        "material_type": "pdf",
        "source_type": "file",
        "file_url": "usr_7196b935728b4f7dad978df363e989ca/crs_c7960168afc743c58a2322dbc4453d97/mat_0def5fcae3d54728b4e89277a0ad1186/source.pdf",
        "source_url": null,
        "file_size": 7441961,
        "mime_type": "application/pdf",
        "parse_status": "uploaded",
        "parse_error": null,
        "page_count": null,
        "created_at": "2026-07-11T16:48:06",
        "updated_at": "2026-07-11T16:48:06",
        "deleted_at": null
      },
      "meta": {
        "request_id": "req_b0f9c7052125462f8b620e2919c5d4cb",
        "server_time": "2026-07-11T16:48:06.432371+00:00",
        "api_version": "v1"
      }
    }
  },
  "materials.parse_retry": {
    "status_code": 200,
    "body": {
      "data": {
        "id": "mat_0def5fcae3d54728b4e89277a0ad1186",
        "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
        "user_id": "usr_7196b935728b4f7dad978df363e989ca",
        "folder_id": null,
        "name": "第12章 保护和安全3课时.pdf",
        "material_type": "pdf",
        "source_type": "file",
        "file_url": "usr_7196b935728b4f7dad978df363e989ca/crs_c7960168afc743c58a2322dbc4453d97/mat_0def5fcae3d54728b4e89277a0ad1186/source.pdf",
        "source_url": null,
        "file_size": 7441961,
        "mime_type": "application/pdf",
        "parse_status": "parsed",
        "parse_error": null,
        "page_count": null,
        "created_at": "2026-07-11T16:48:06",
        "updated_at": "2026-07-11T16:48:56.896361",
        "deleted_at": null
      },
      "meta": {
        "request_id": "req_54a8bb8793d841259b41c609743cbe44",
        "server_time": "2026-07-11T16:48:56.898363+00:00",
        "api_version": "v1"
      }
    }
  },
  "study_plan_config_parse": {
    "status_code": 200,
    "body": {
      "data": {
        "goal_text": "我要两天学完操作系统这门课的第十二章",
        "start_date": null,
        "end_date": null,
        "daily_available_minutes": null,
        "preference": null,
        "material_scope": {
          "include_all_parsed_materials": true,
          "material_ids": []
        },
        "unresolved_fields": [
          "start_date",
          "end_date",
          "daily_available_minutes",
          "preference"
        ]
      },
      "meta": {
        "request_id": "req_9e75902f5d554830908020542249170c",
        "server_time": "2026-07-11T16:48:58.471138+00:00",
        "api_version": "v1"
      }
    }
  },
  "study_plans.preview": {
    "status_code": 200,
    "body": {
      "data": {
        "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
        "title": "两天学完操作系统第十二章",
        "goal_text": "我要两天学完操作系统这门课的第十二章",
        "start_date": "2026-07-12",
        "end_date": "2026-07-13",
        "daily_available_minutes": 180,
        "preference": "balanced",
        "material_scope": {
          "include_all_parsed_materials": true,
          "material_ids": []
        },
        "coverage": {
          "expected_material_ids": [
            "mat_0def5fcae3d54728b4e89277a0ad1186"
          ],
          "processed_material_ids": [
            "mat_0def5fcae3d54728b4e89277a0ad1186"
          ],
          "batch_count": 1
        },
        "tasks": [
          {
            "title": "第一天：安全环境与加密技术",
            "task_date": "2026-07-12",
            "sort_order": 1,
            "subtasks": [
              {
                "title": "安全环境概述",
                "subtask_type": "learn",
                "description": "介绍保护与安全的定义、安全目标（机密性、完整性、可用性）以及计算机安全评价标准（TCSEC分级）。",
                "related_material_ids": [
                  "mat_0def5fcae3d54728b4e89277a0ad1186"
                ],
                "estimated_minutes": 50,
                "citation_chunk_ids": [
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000002",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000003",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000004",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000005"
                ],
                "sort_order": 1
              },
              {
                "title": "数据加密技术",
                "subtask_type": "learn",
                "description": "讲解加密模型、基本加密方法（易位法和置换法）以及HTTPS中的对称与非对称加密概念。",
                "related_material_ids": [
                  "mat_0def5fcae3d54728b4e89277a0ad1186"
                ],
                "estimated_minutes": 70,
                "citation_chunk_ids": [
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000006",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000007",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000008",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000009",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000010",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000011",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000012",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000013"
                ],
                "sort_order": 2
              },
              {
                "title": "用户验证与攻击",
                "subtask_type": "learn",
                "description": "涵盖用户验证技术及来自系统内部和外部的攻击类型（如数据篡改、拒绝服务等）。",
                "related_material_ids": [
                  "mat_0def5fcae3d54728b4e89277a0ad1186"
                ],
                "estimated_minutes": 30,
                "citation_chunk_ids": [
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000001"
                ],
                "sort_order": 3
              },
              {
                "title": "可信系统",
                "subtask_type": "learn",
                "description": "介绍可信系统的概念及安全等级（B3、A1等）特征。",
                "related_material_ids": [
                  "mat_0def5fcae3d54728b4e89277a0ad1186"
                ],
                "estimated_minutes": 30,
                "citation_chunk_ids": [
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000001"
                ],
                "sort_order": 4
              }
            ]
          },
          {
            "title": "第二天：复习与测验",
            "task_date": "2026-07-13",
            "sort_order": 2,
            "subtasks": [
              {
                "title": "复习第十二章内容",
                "subtask_type": "review",
                "description": "复习安全环境、加密、用户验证、攻击类型和可信系统。",
                "related_material_ids": [
                  "mat_0def5fcae3d54728b4e89277a0ad1186"
                ],
                "estimated_minutes": 60,
                "citation_chunk_ids": [
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000000",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000001",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000002",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000003",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000004",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000005",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000006",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000007",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000008",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000009",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000010",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000011",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000012",
                  "chk_0def5fcae3d54728b4e89277a0ad1186_000013"
                ],
                "sort_order": 1
              },
              {
                "title": "章节测验",
                "subtask_type": "quiz",
                "description": "完成第十二章的测验题目。",
                "related_material_ids": [
                  "mat_0def5fcae3d54728b4e89277a0ad1186"
                ],
                "estimated_minutes": 60,
                "citation_chunk_ids": [],
                "sort_order": 2
              },
              {
                "title": "综合测试",
                "subtask_type": "test",
                "description": "进行第十二章的综合测试。",
                "related_material_ids": [
                  "mat_0def5fcae3d54728b4e89277a0ad1186"
                ],
                "estimated_minutes": 60,
                "citation_chunk_ids": [],
                "sort_order": 3
              }
            ]
          }
        ]
      },
      "meta": {
        "request_id": "req_b12794f8b0084c23a6ecc42da9897b67",
        "server_time": "2026-07-11T16:49:19.536459+00:00",
        "api_version": "v1"
      }
    }
  },
  "study_plans.save": {
    "status_code": 200,
    "body": {
      "data": {
        "plan": {
          "id": "sp_03e0314fa07141a5a86f18a42003402b",
          "user_id": "usr_7196b935728b4f7dad978df363e989ca",
          "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
          "title": "两天学完操作系统第十二章",
          "goal_text": "我要两天学完操作系统这门课的第十二章",
          "parsed_config_json": {
            "material_scope": {
              "include_all_parsed_materials": true,
              "material_ids": []
            },
            "daily_available_minutes": 180,
            "preference": "balanced",
            "tasks_source": "confirmed",
            "idempotency": {
              "key_hash": "2270efeb1c07a5510d188893043baf843c7a3498ee1132ea5cbb08c066d985da",
              "request_hash": "68352e400cb62e3b283252148e2e7e8ab0937562088a66d147d50803ab81f64c"
            }
          },
          "start_date": "2026-07-12",
          "end_date": "2026-07-13",
          "daily_available_minutes": 180,
          "status": "active",
          "created_at": "2026-07-11T16:49:19",
          "updated_at": "2026-07-11T16:49:19",
          "deleted_at": null
        },
        "tasks": [
          {
            "id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "第一天：安全环境与加密技术",
            "task_date": "2026-07-12",
            "status": "not_started",
            "sort_order": 1,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          },
          {
            "id": "tsk_08abda047163400f95ded274b709a01d",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "第二天：复习与测验",
            "task_date": "2026-07-13",
            "status": "not_started",
            "sort_order": 2,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          }
        ],
        "subtasks": [
          {
            "id": "sub_3b44142807a1450fa6cc0966d2dc19a6",
            "task_id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "安全环境概述",
            "subtask_type": "learn",
            "description": "介绍保护与安全的定义、安全目标（机密性、完整性、可用性）以及计算机安全评价标准（TCSEC分级）。",
            "related_material_ids_json": [
              "mat_0def5fcae3d54728b4e89277a0ad1186"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 1,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          },
          {
            "id": "sub_17ad3f3a2729463aa6a9c019f658f233",
            "task_id": "tsk_08abda047163400f95ded274b709a01d",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "复习第十二章内容",
            "subtask_type": "review",
            "description": "复习安全环境、加密、用户验证、攻击类型和可信系统。",
            "related_material_ids_json": [
              "mat_0def5fcae3d54728b4e89277a0ad1186"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 1,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          },
          {
            "id": "sub_b1f4b4d2368340879f3cc1bfa9df707a",
            "task_id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "数据加密技术",
            "subtask_type": "learn",
            "description": "讲解加密模型、基本加密方法（易位法和置换法）以及HTTPS中的对称与非对称加密概念。",
            "related_material_ids_json": [
              "mat_0def5fcae3d54728b4e89277a0ad1186"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 2,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          },
          {
            "id": "sub_7c442e974eee407f8b2570851721041b",
            "task_id": "tsk_08abda047163400f95ded274b709a01d",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "章节测验",
            "subtask_type": "quiz",
            "description": "完成第十二章的测验题目。",
            "related_material_ids_json": [
              "mat_0def5fcae3d54728b4e89277a0ad1186"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 2,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          },
          {
            "id": "sub_99bf631b1c4e466f90d9b808fa277643",
            "task_id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "用户验证与攻击",
            "subtask_type": "learn",
            "description": "涵盖用户验证技术及来自系统内部和外部的攻击类型（如数据篡改、拒绝服务等）。",
            "related_material_ids_json": [
              "mat_0def5fcae3d54728b4e89277a0ad1186"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 3,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          },
          {
            "id": "sub_f8f5fbeb5087451f841809c82d2b2ae7",
            "task_id": "tsk_08abda047163400f95ded274b709a01d",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "综合测试",
            "subtask_type": "test",
            "description": "进行第十二章的综合测试。",
            "related_material_ids_json": [
              "mat_0def5fcae3d54728b4e89277a0ad1186"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 3,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          },
          {
            "id": "sub_8e10dbc0505b44e8bd2f361eb001e3a6",
            "task_id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "可信系统",
            "subtask_type": "learn",
            "description": "介绍可信系统的概念及安全等级（B3、A1等）特征。",
            "related_material_ids_json": [
              "mat_0def5fcae3d54728b4e89277a0ad1186"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 4,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          }
        ]
      },
      "meta": {
        "request_id": "req_0a7b75ba4991463da98ca88053af744a",
        "server_time": "2026-07-11T16:49:19.565776+00:00",
        "api_version": "v1"
      }
    }
  },
  "study_plans.list": {
    "status_code": 200,
    "body": {
      "data": [
        {
          "id": "sp_03e0314fa07141a5a86f18a42003402b",
          "user_id": "usr_7196b935728b4f7dad978df363e989ca",
          "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
          "title": "两天学完操作系统第十二章",
          "goal_text": "我要两天学完操作系统这门课的第十二章",
          "parsed_config_json": {
            "material_scope": {
              "include_all_parsed_materials": true,
              "material_ids": []
            },
            "daily_available_minutes": 180,
            "preference": "balanced",
            "tasks_source": "confirmed",
            "idempotency": {
              "key_hash": "2270efeb1c07a5510d188893043baf843c7a3498ee1132ea5cbb08c066d985da",
              "request_hash": "68352e400cb62e3b283252148e2e7e8ab0937562088a66d147d50803ab81f64c"
            }
          },
          "start_date": "2026-07-12",
          "end_date": "2026-07-13",
          "daily_available_minutes": 180,
          "status": "active",
          "created_at": "2026-07-11T16:49:19",
          "updated_at": "2026-07-11T16:49:19",
          "deleted_at": null
        }
      ],
      "meta": {
        "request_id": "req_385e640a8a834677b59ca84d94a70286",
        "server_time": "2026-07-11T16:49:19.574099+00:00",
        "api_version": "v1"
      }
    }
  },
  "study_plans.detail": {
    "status_code": 200,
    "body": {
      "data": {
        "plan": {
          "id": "sp_03e0314fa07141a5a86f18a42003402b",
          "user_id": "usr_7196b935728b4f7dad978df363e989ca",
          "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
          "title": "两天学完操作系统第十二章",
          "goal_text": "我要两天学完操作系统这门课的第十二章",
          "parsed_config_json": {
            "material_scope": {
              "include_all_parsed_materials": true,
              "material_ids": []
            },
            "daily_available_minutes": 180,
            "preference": "balanced",
            "tasks_source": "confirmed",
            "idempotency": {
              "key_hash": "2270efeb1c07a5510d188893043baf843c7a3498ee1132ea5cbb08c066d985da",
              "request_hash": "68352e400cb62e3b283252148e2e7e8ab0937562088a66d147d50803ab81f64c"
            }
          },
          "start_date": "2026-07-12",
          "end_date": "2026-07-13",
          "daily_available_minutes": 180,
          "status": "active",
          "created_at": "2026-07-11T16:49:19",
          "updated_at": "2026-07-11T16:49:19",
          "deleted_at": null
        },
        "tasks": [
          {
            "id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "第一天：安全环境与加密技术",
            "task_date": "2026-07-12",
            "status": "not_started",
            "sort_order": 1,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          },
          {
            "id": "tsk_08abda047163400f95ded274b709a01d",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "第二天：复习与测验",
            "task_date": "2026-07-13",
            "status": "not_started",
            "sort_order": 2,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          }
        ],
        "subtasks": [
          {
            "id": "sub_3b44142807a1450fa6cc0966d2dc19a6",
            "task_id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "安全环境概述",
            "subtask_type": "learn",
            "description": "介绍保护与安全的定义、安全目标（机密性、完整性、可用性）以及计算机安全评价标准（TCSEC分级）。",
            "related_material_ids_json": [
              "mat_0def5fcae3d54728b4e89277a0ad1186"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 1,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          },
          {
            "id": "sub_17ad3f3a2729463aa6a9c019f658f233",
            "task_id": "tsk_08abda047163400f95ded274b709a01d",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "复习第十二章内容",
            "subtask_type": "review",
            "description": "复习安全环境、加密、用户验证、攻击类型和可信系统。",
            "related_material_ids_json": [
              "mat_0def5fcae3d54728b4e89277a0ad1186"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 1,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          },
          {
            "id": "sub_b1f4b4d2368340879f3cc1bfa9df707a",
            "task_id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "数据加密技术",
            "subtask_type": "learn",
            "description": "讲解加密模型、基本加密方法（易位法和置换法）以及HTTPS中的对称与非对称加密概念。",
            "related_material_ids_json": [
              "mat_0def5fcae3d54728b4e89277a0ad1186"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 2,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          },
          {
            "id": "sub_7c442e974eee407f8b2570851721041b",
            "task_id": "tsk_08abda047163400f95ded274b709a01d",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "章节测验",
            "subtask_type": "quiz",
            "description": "完成第十二章的测验题目。",
            "related_material_ids_json": [
              "mat_0def5fcae3d54728b4e89277a0ad1186"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 2,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          },
          {
            "id": "sub_99bf631b1c4e466f90d9b808fa277643",
            "task_id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "用户验证与攻击",
            "subtask_type": "learn",
            "description": "涵盖用户验证技术及来自系统内部和外部的攻击类型（如数据篡改、拒绝服务等）。",
            "related_material_ids_json": [
              "mat_0def5fcae3d54728b4e89277a0ad1186"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 3,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          },
          {
            "id": "sub_f8f5fbeb5087451f841809c82d2b2ae7",
            "task_id": "tsk_08abda047163400f95ded274b709a01d",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "综合测试",
            "subtask_type": "test",
            "description": "进行第十二章的综合测试。",
            "related_material_ids_json": [
              "mat_0def5fcae3d54728b4e89277a0ad1186"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 3,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          },
          {
            "id": "sub_8e10dbc0505b44e8bd2f361eb001e3a6",
            "task_id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
            "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
            "course_id": "crs_c7960168afc743c58a2322dbc4453d97",
            "title": "可信系统",
            "subtask_type": "learn",
            "description": "介绍可信系统的概念及安全等级（B3、A1等）特征。",
            "related_material_ids_json": [
              "mat_0def5fcae3d54728b4e89277a0ad1186"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 4,
            "created_at": "2026-07-11T16:49:19",
            "updated_at": "2026-07-11T16:49:19"
          }
        ]
      },
      "meta": {
        "request_id": "req_ed8d03ab5c0f45688cb2dd38b799d507",
        "server_time": "2026-07-11T16:49:19.584096+00:00",
        "api_version": "v1"
      }
    }
  }
}
```

## 数据库落库结果

```json
{
  "study_plans": [
    {
      "id": "sp_03e0314fa07141a5a86f18a42003402b",
      "title": "两天学完操作系统第十二章",
      "goal_text": "我要两天学完操作系统这门课的第十二章",
      "start_date": "2026-07-12",
      "end_date": "2026-07-13",
      "daily_available_minutes": 180,
      "status": "active",
      "parsed_config_json": {
        "material_scope": {
          "include_all_parsed_materials": true,
          "material_ids": []
        },
        "daily_available_minutes": 180,
        "preference": "balanced",
        "tasks_source": "confirmed",
        "idempotency": {
          "key_hash": "2270efeb1c07a5510d188893043baf843c7a3498ee1132ea5cbb08c066d985da",
          "request_hash": "68352e400cb62e3b283252148e2e7e8ab0937562088a66d147d50803ab81f64c"
        }
      }
    }
  ],
  "study_tasks": [
    {
      "id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
      "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
      "title": "第一天：安全环境与加密技术",
      "task_date": "2026-07-12",
      "status": "not_started",
      "sort_order": 1
    },
    {
      "id": "tsk_08abda047163400f95ded274b709a01d",
      "plan_id": "sp_03e0314fa07141a5a86f18a42003402b",
      "title": "第二天：复习与测验",
      "task_date": "2026-07-13",
      "status": "not_started",
      "sort_order": 2
    }
  ],
  "study_subtasks": [
    {
      "id": "sub_3b44142807a1450fa6cc0966d2dc19a6",
      "task_id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
      "title": "安全环境概述",
      "subtask_type": "learn",
      "description": "介绍保护与安全的定义、安全目标（机密性、完整性、可用性）以及计算机安全评价标准（TCSEC分级）。",
      "related_material_ids_json": [
        "mat_0def5fcae3d54728b4e89277a0ad1186"
      ],
      "status": "not_started",
      "sort_order": 1
    },
    {
      "id": "sub_17ad3f3a2729463aa6a9c019f658f233",
      "task_id": "tsk_08abda047163400f95ded274b709a01d",
      "title": "复习第十二章内容",
      "subtask_type": "review",
      "description": "复习安全环境、加密、用户验证、攻击类型和可信系统。",
      "related_material_ids_json": [
        "mat_0def5fcae3d54728b4e89277a0ad1186"
      ],
      "status": "not_started",
      "sort_order": 1
    },
    {
      "id": "sub_b1f4b4d2368340879f3cc1bfa9df707a",
      "task_id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
      "title": "数据加密技术",
      "subtask_type": "learn",
      "description": "讲解加密模型、基本加密方法（易位法和置换法）以及HTTPS中的对称与非对称加密概念。",
      "related_material_ids_json": [
        "mat_0def5fcae3d54728b4e89277a0ad1186"
      ],
      "status": "not_started",
      "sort_order": 2
    },
    {
      "id": "sub_7c442e974eee407f8b2570851721041b",
      "task_id": "tsk_08abda047163400f95ded274b709a01d",
      "title": "章节测验",
      "subtask_type": "quiz",
      "description": "完成第十二章的测验题目。",
      "related_material_ids_json": [
        "mat_0def5fcae3d54728b4e89277a0ad1186"
      ],
      "status": "not_started",
      "sort_order": 2
    },
    {
      "id": "sub_99bf631b1c4e466f90d9b808fa277643",
      "task_id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
      "title": "用户验证与攻击",
      "subtask_type": "learn",
      "description": "涵盖用户验证技术及来自系统内部和外部的攻击类型（如数据篡改、拒绝服务等）。",
      "related_material_ids_json": [
        "mat_0def5fcae3d54728b4e89277a0ad1186"
      ],
      "status": "not_started",
      "sort_order": 3
    },
    {
      "id": "sub_f8f5fbeb5087451f841809c82d2b2ae7",
      "task_id": "tsk_08abda047163400f95ded274b709a01d",
      "title": "综合测试",
      "subtask_type": "test",
      "description": "进行第十二章的综合测试。",
      "related_material_ids_json": [
        "mat_0def5fcae3d54728b4e89277a0ad1186"
      ],
      "status": "not_started",
      "sort_order": 3
    },
    {
      "id": "sub_8e10dbc0505b44e8bd2f361eb001e3a6",
      "task_id": "tsk_70dab05b3fd145d9b79fef5396df1c3f",
      "title": "可信系统",
      "subtask_type": "learn",
      "description": "介绍可信系统的概念及安全等级（B3、A1等）特征。",
      "related_material_ids_json": [
        "mat_0def5fcae3d54728b4e89277a0ad1186"
      ],
      "status": "not_started",
      "sort_order": 4
    }
  ],
  "checkin_records": [
    {
      "id": "chkrec_8d0dc8eb99b7452c8b01e5e90bcc0ebe",
      "checkin_date": "2026-07-12",
      "total_subtask_count": 4,
      "completed_subtask_count": 0,
      "completion_ratio": "0.0000",
      "color_level": 1
    },
    {
      "id": "chkrec_7c78997fbb834609a232de6989a866f0",
      "checkin_date": "2026-07-13",
      "total_subtask_count": 3,
      "completed_subtask_count": 0,
      "completion_ratio": "0.0000",
      "color_level": 1
    }
  ]
}
```
