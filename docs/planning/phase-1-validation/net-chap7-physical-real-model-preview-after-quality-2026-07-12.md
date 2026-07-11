# 计网第七章学习计划真实模型回归报告（质量约束后）

## 基本信息

- 运行时间：`2026-07-12T02:58:19`

- 结果：`failed`

- 自然语言：`我要两天学完计网这门课的第七章节，今天是2026年7月12日`

- 课程：`计算机网络`

- 资料：`D:\大二下课程\计算机网络\课件\Chap7 物理层.pdf`

- 默认每日可用时间：`180` 分钟（自然语言未给出时用于测试归一化）


## 模型配置检查（已脱敏）

```json
{
  "study_plan_parser": {
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com",
    "api_key_configured": true,
    "api_key_redacted": "***configured***"
  },
  "study_plan_generator": {
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com",
    "api_key_configured": true,
    "api_key_redacted": "***configured***"
  }
}
```

## 资料解析输出

```json
{
  "material_id": "mat_1fbc7d6e822e4f8b97ebe60e622e6f77",
  "material_name": "Chap7 物理层.pdf",
  "parse_status": "parsed",
  "parse_error": null,
  "chunk_count": 15,
  "formula_placeholder_count": 1,
  "pages_with_chunks": [
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "9",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "16",
    "32"
  ]
}
```

### 解析 Chunk 摘要（前 30 个）

```json
[
  {
    "chunk_index": 0,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000000",
    "page": "2",
    "heading": " 7.1 物理层概述",
    "text_excerpt": "-  7.2 数据通信的基础知识\n-  7.3 传输介质\n-  7.4 调制技术和编码技术\n-  7.5 复用技术\n-  7.6 物理层互连设备\n-  7.7 物理层的安全隐患"
  },
  {
    "chunk_index": 1,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000001",
    "page": "3",
    "heading": "教学内容及要求",
    "text_excerpt": "-  掌握物理层的功能和主要概念\n-  掌握数据通信的基本概念和理论基础：\n-  Nyquest 公式和 Shannon 公式\n-  掌握常用的调制、编码和复用的方法要点\n-  了解 HUB 的功能\n-  了解物理层的安全隐患"
  },
  {
    "chunk_index": 2,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000002",
    "page": "4",
    "heading": "物理层的位置和基本功能",
    "text_excerpt": "-  网络体系结构的最底层，实现真正的数据传输\n-  将二进制数据编码或调制成信号，发送到传输介质 ( 传输媒体 )\n-  从传输介质接收信号，转换成二进制数据"
  },
  {
    "chunk_index": 3,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000003",
    "page": "5",
    "heading": "物理层的主要功能",
    "text_excerpt": "-  规定了与传输介质的接口的特性\n-  机械特性：规定接口所用接线器的形状和尺寸、引 线数目和排列等\n-  电气特性：规定在接口电缆的各条线上的电压范围\n-  功能特性：规定接口电缆的某条线出现某一电平的 含义\n-  规程特性：规定各种可能事件的出现顺序"
  },
  {
    "chunk_index": 4,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000004",
    "page": "6",
    "heading": "物理层协议示例",
    "text_excerpt": "-  IEEE802.3 ， 10BaseT\n-  数据率 10Mbps ，传输介质为双绞线，拓扑结构为星形\n-  物理接口的特性\n-  机械特性： RJ45 接口\n-  电气特性：\n-  Manchester 编码\n-  电平： 2.5v ， -2.5v\n-  功能特性：\n-  一对线发送（ 1,2 针）、一对线接收（ 3,6 针）\n-  全双工通信\nRJ-45 Female\nRJ-45 Male"
  },
  {
    "chunk_index": 5,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000005",
    "page": "7",
    "heading": "主要内容",
    "text_excerpt": "-  7.1 物理层概述\n-  7.2 数据通信的基础知识\n-  7.3 传输介质\n-  7.4 调制技术和编码技术\n-  7.5 复用技术\n-  7.6 物理层互连设备\n-  7.7 物理层的安全隐患"
  },
  {
    "chunk_index": 6,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000006",
    "page": "9",
    "heading": " 信息、数据与信号",
    "text_excerpt": "-  信息：人类知识的表征，通信的目的就是传输信息。 信息的载体包括数字、文字、语音、图形或图像。\n-  数据：承载信息的实体，以二进制的形式在计算机 系统中处理。\n-  信号：数据的电平或电磁波形式表示，在传输介质 上传播。\n-  码元：基本信号单位\n-  码元的速率称为波特率 (Baud)"
  },
  {
    "chunk_index": 7,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000007",
    "page": "10",
    "heading": "模拟信号与数字信号",
    "text_excerpt": "-  模拟信号 (Analog Signal) ：信号的幅度随时间 连续变化。\n-  数字信号 (Digital Signal) ：离散的电平值"
  },
  {
    "chunk_index": 8,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000008",
    "page": "11",
    "heading": "信道：信号的通道",
    "text_excerpt": "-  狭义的信道指的是连接两个设备之间的传输介质，即 物理链路（计算机网络课程范畴使用）\n-  广义的信道指的是信号传输的整个路径，中间可能经 过多个设备，如因特网上位于不同城市的两台计算机 之间的通路\n-  模拟信道以连续的电磁波形式来传输数据； 数字信道以离散的数字脉冲形式传输数据"
  },
  {
    "chunk_index": 9,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000009",
    "page": "12",
    "heading": "模拟通信与数字通信",
    "text_excerpt": "-  模拟通信：信道中传输的是模拟信号，如有线电 视系统中的通信\n-  信道利用率高，但传输质量差\n-  数字通信：信道中传输的是数字信号，如因特网 上的通信\n-  衰减低，抗干扰性强\n-  信道利用率较低\n-  模拟信道上传输的不一定是模拟数据，反之亦然"
  },
  {
    "chunk_index": 10,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000010",
    "page": "13",
    "heading": "数据率与带宽",
    "text_excerpt": "-  带宽：信道传输电磁波信号的频率范围（可通 过的最高频率 -最低频率），单位： Hz\n-  数据率：信道的最大传输速率，单位： bps"
  },
  {
    "chunk_index": 11,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000011",
    "page": "14",
    "heading": "最大数据率（信道容量）",
    "text_excerpt": "-  为什么信道容量有上限？\n-  信号失真（码间串扰）\n-  码元传输速度过高\n-  信号传输距离过远\n-  传输介质质量差\n-  噪声干扰\n-  如何计算最大数据率（极限信道容量）？\n-  奈奎斯特（ Nyquist ）公式：用于无噪声信道\n-  香农（ Shannon ）公式：用于噪声信道"
  },
  {
    "chunk_index": 12,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000012",
    "page": "15",
    "heading": "最大数据率（信道容量）公式",
    "text_excerpt": "-  奈奎斯特（ Nyquist ）公式：用于无噪声信道\n<!-- formula-not-decoded -->\n-  C ：最大数据率， B ：带宽， L ：信号级数\n-  香农（ Shannon ）公式：用于噪声信道\n<!-- formula-not-decoded -->\n-  S/N ：信噪比\n-  单位为分贝， dB 值 =10 × lg(S/N)"
  },
  {
    "chunk_index": 13,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000013",
    "page": "16",
    "heading": "主要内容",
    "text_excerpt": "-  7.1 物理层概述\n-  7.2 数据通信的基础知识\n-  7.3 传输介质\n-  7.4 调制技术和编码技术\n-  7.5 复用技术\n-  7.6 物理层互连设备\n-  7.7 物理层的安全隐患"
  },
  {
    "chunk_index": 14,
    "chunk_id": "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000014",
    "page": "32",
    "heading": "数字数据编码技术",
    "text_excerpt": "NRZ-L\n不归零编码\n不归零反向编码 NRZI\n曼彻斯特编码 Manchester\nDifferential manchester\n差分曼彻斯特"
  }
]
```

## 自然语言配置解析

```json
{
  "goal_text": "我要两天学完计网这门课的第七章节",
  "start_date": "2026-07-12",
  "end_date": "2026-07-13",
  "daily_available_minutes": null,
  "preference": null,
  "material_scope": {
    "include_all_parsed_materials": true,
    "material_ids": []
  },
  "unresolved_fields": [
    "daily_available_minutes",
    "preference"
  ]
}
```

## 构造后的计划请求

```json
{
  "goal_text": "我要两天学完计网这门课的第七章节，今天是2026年7月12日",
  "start_date": "2026-07-12",
  "end_date": "2026-07-13",
  "daily_available_minutes": 180,
  "material_scope": {
    "include_all_parsed_materials": true,
    "material_ids": []
  }
}
```

## 模型调用记录

### Parser Provider Calls

```json
[
  {
    "purpose": "study_plan_parser",
    "schema": "StudyPlanParsedConfig",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com",
    "api_key_configured": true,
    "prompt_sha256": "7660c373be58c4a05206a538f3af05bdf2593e9508d63a59c98347a638c9cb08",
    "prompt_excerpt": "你是 CourseNexus 的学习计划配置解析器。\n只从用户目标中提取可编辑的学习计划字段，不创建计划，不编造无法确定的信息。\n无法可靠确定的字段填 null，并把字段名加入 unresolved_fields。\n相对日期解析规则：当用户写“今天是 YYYY年M月D日”时，可把该日期作为当前日期。\n当用户写“两天学完”且给出今天日期时，start_date 为当天，end_date 为当天 + 1 天。\n当用户写“N天学完/掌握/完成”且给出今天日期时，start_date 为当天，end_date 为当天 + (N - 1) 天。\n课程名称：计算机网络\n用户目标：我要两天学完计网这门课的第七章节，今天是2026年7月12日\n资料范围：{'include_all_parsed_materials': True, 'material_ids': []}",
    "status": "ok",
    "elapsed_seconds": 2.14,
    "output": {
      "goal_text": "我要两天学完计网这门课的第七章节",
      "start_date": "2026-07-12",
      "end_date": "2026-07-13",
      "daily_available_minutes": null,
      "preference": null,
      "material_scope": {
        "include_all_parsed_materials": true,
        "material_ids": []
      },
      "unresolved_fields": [
        "daily_available_minutes",
        "preference"
      ]
    }
  }
]
```

### Generator Provider Calls

```json
[
  {
    "purpose": "study_plan_generator",
    "schema": "PlanBatchExtraction",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com",
    "api_key_configured": true,
    "prompt_sha256": "5d98eb0d800358f1529fa43decc7c85165378b013daf548fcdfe8cdf19d1a146",
    "prompt_excerpt": "你是 CourseNexus 的学习计划材料分析器。\n请把本批资料提炼为可排入学习计划的知识单元。\n按 chunk 出现顺序、章节/页码顺序覆盖资料，不要只输出章节级摘要。\n把公式、标准、接口示例、典型设备、调制/编码/复用方法和安全隐患拆成可学习的细粒度知识点。\n每个有实质内容的 chunk 必须被至少一个知识单元引用，或在相邻知识单元 summary 中说明已合并。\n遇到 <!-- formula-not-decoded -->、图片、表格或图示缺失时，在 summary 中写明需人工复核。\n每个 PlanMaterialUnit 的 citation_chunk_ids 必须来自输入 chunk_id，不能留空。\n网络类资料要特别保留 10BaseT/RJ45、ASK、FSK、PSK、PCM、WDM、STDM、HUB、冲突域等具体术语。\ngoal_text: 我要两天学完计网这门课的第七章节，今天是2026年7月12日\ndate_range: 2026-07-12 to 2026-07-13\ndaily_available_minutes: 180\nmaterial_ids: mat_1fbc7d6e822e4f8b97ebe60e622e6f77\nchunks:\nchunk_id=chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000000 material_id=mat_1fbc7d6e822e4f8b97ebe60e622e6f77 page=2 heading= 7.1 物理层概述 text=-  7.2 数据通信的基础知识\n-  7.3 传输介质\n-  7.4 调制技术和编码技术\n-  7.5 复用技术\n-  7.6 物理层互连设备\n-  7.7 物理层的安全隐患\nchunk_id=chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000001 material_id=mat_1fbc7d6e822e4f8b97ebe60e622e6f77 page=3 heading=教学内容及要求 text=-  掌握物理层的功能和主要概念\n-  掌握数据通信的基本概念和理论基础：\n-  Nyquest 公式和 Shannon 公式\n-  掌握常用的调制、编码和复用的方法要点\n-  了解 HUB 的功能\n-  了解物理层的安全隐患\nchunk_id=chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000002 material_id=mat_1fbc7d6e822e4f8b97ebe60e622e6f77 page=4 heading=物理层的位置和基本功能 text=-  网络体系结构的最底层，实现真正的数据传输\n-  将二进制数据编码或调制成信号，发送到传输介质 ( 传输媒体 )\n-  从传输介质接收信号，转换成二进制数据\nchunk_id=chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000003 material_id=mat_1fbc7d6e822e4f8b97ebe60e622e6f77 page=5 heading=物理层的主要功能 text=-  规定了与传输介质的接口的特性\n-  机械特性：规定接口所用接线器的形状和尺寸、引 线数目和排列等\n-  电气特性：规定在接口电缆的各条线上的电压范围\n-  功能特性：规定接口电缆的某条线出现某一电平的 含义\n-  规程特性：规定各种可能事件的出现顺序\nchunk_id=chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000004 material_id=mat_1fbc7d6e822e4f8b97ebe60e622e6f77 page=6 heading=物理层协议示例 text=-  IEEE802.3 ， 10BaseT\n-  数据率 10Mbps ，传输介质为双绞线，拓扑结构为星形\n-  物理接口的特性\n-  机械特性： RJ45 接口\n-  电气特性：\n-  Manchester 编码\n-  电平： 2.5v ， -2.5v\n-  功能特性：\n-  一对线发送（ 1,2 针）、一对线接收（ 3,6 针）\n-  全双工通信\nRJ-45 Female\nRJ-45 Male\nchunk_id=chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000005 material_id=mat_1fbc7d6e822e4f8b97ebe60e622e6f77 page=7 heading=主要内容 text=-  7.1 物理层概述\n-  7.2 数据通信的基础知识\n-  7.3 传输介质\n-  7.4 调制技术和编码技术\n-  7.5 复用技术\n-  7.6 物理层互连设备\n-  7.7 物理层的安全隐患\nchunk_id=chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000006 material_id=mat_1fbc7d6e822e4f8b97ebe60e622e6f77 page=9 heading= 信息、数据与信号 text=-  信息：人类知识的表征，通信的目的就是传输信息。 信息的载体包括数字、文字、语音、图形或图像。\n-  数据：承载信息的实体，以二进制的形式在计算机 系统中处理。\n-  信号：数据的电平或电磁波形式表示，在传输介质 上传播。\n-  码元：基本信号单位\n-  码元的速率称为波特率 (Baud)\nchunk_id=chk_1fbc7d6e822e4f8b9\n...<truncated>",
    "status": "ok",
    "elapsed_seconds": 11.447,
    "output": {
      "units": [
        {
          "topic": "物理层概述与功能",
          "summary": "物理层位于网络体系结构最底层，实现二进制数据与信号之间的转换（编码/调制发送，接收解调/解码）。主要功能包括：机械特性、电气特性、功能特性、规程特性。",
          "difficulty": "easy",
          "estimated_minutes": 15,
          "related_material_ids": [
            "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
          ],
          "citation_chunk_ids": [
            "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000002",
            "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000003"
          ]
        },
        {
          "topic": "物理层协议示例：IEEE802.3 10BaseT与RJ45",
          "summary": "以IEEE802.3 10BaseT为例，数据率10Mbps，双绞线介质，星形拓扑。RJ45接口机械特性，Manchester编码电气特性（2.5V/-2.5V），功能特性：1、2针发送，3、6针接收，全双工通信。",
          "difficulty": "medium",
          "estimated_minutes": 20,
          "related_material_ids": [
            "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
          ],
          "citation_chunk_ids": [
            "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000004"
          ]
        },
        {
          "topic": "信息、数据、信号与码元",
          "summary": "信息是人类知识的表征；数据是信息二进制载体；信号是数据的电平或电磁波表示；码元是基本信号单位，波特率表示码元速率。模拟信号连续变化，数字信号离散电平。信道分类：狭义物理链路，广义整个路径；模拟信道传输连续电磁波，数字信道传输离散脉冲。模拟通信信道利用率高但质量差，数字通信抗干扰性强但利用率较低。数据通信基础知识：带宽（Hz）、数据率（bps）。",
          "difficulty": "easy",
          "estimated_minutes": 15,
          "related_material_ids": [
            "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
          ],
          "citation_chunk_ids": [
            "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000006",
            "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000007",
            "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000008",
            "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000009",
            "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000010"
          ]
        },
        {
          "topic": "信道容量：奈奎斯特与香农公式",
          "summary": "信号失真原因（码间串扰）：码元速率过高、距离过远、介质差、噪声干扰。无噪声信道最大数据率用奈奎斯特公式：C=2B log2(L)（B带宽，L信号级数）。噪声信道用香农公式：C=B log2(1+S/N)（S/N信噪比，dB=10lg(S/N)）。注意公式需人工复核（标记<!-- formula-not-decoded -->）。",
          "difficulty": "hard",
          "estimated_minutes": 25,
          "related_material_ids": [
            "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
          ],
          "citation_chunk_ids": [
            "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000011",
            "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000012"
          ]
        },
        {
          "topic": "数字数据编码技术",
          "summary": "常见编码方式：NRZ-L（不归零编码）、NRZI（不归零反向编码）、曼彻斯特编码（Manchester）、差分曼彻斯特编码（Differential Manchester）。",
          "difficulty": "medium",
          "estimated_minutes": 20,
          "related_material_ids": [
            "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
          ],
          "citation_chunk_ids": [
            "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000014"
          ]
        },
        {
          "topic": "教学内容与章节结构",
          "summary": "资料涵盖教学内容要求：物理层功能、数据通信基础（Nyquist/Shannon公式）、调制/编码/复用方法、HUB功能、物理层安全隐患。内容目录包括7.1至7.7。该单元为综述性质，具体知识已在其他单元展开。",
          "difficulty": "easy",
          "estimated_minutes": 5,
          "related_material_ids": [
            "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
          ],
          "citation_chunk_ids": [
            "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000000",
            "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000001",
            "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000005"
          ]
        }
      ],
      "citation_chunk_ids": [
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000000",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000001",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000002",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000003",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000004",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000005",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000006",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000007",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000008",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000009",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000010",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000011",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000012",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000014"
      ]
    }
  },
  {
    "purpose": "study_plan_generator",
    "schema": "StudyPlanReduction",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com",
    "api_key_configured": true,
    "prompt_sha256": "ae1dd52af73dc48f926a0c415281187052648fd8173ac7da59553b766a4d7241",
    "prompt_excerpt": "你是 CourseNexus 的学习计划排程器。\n请把所有材料单元归并为日期连续、可执行的单课程学习计划预览。\n课程名称：计算机网络\n标题必须使用课程名称的原文，不要改写、错写或自行造简称。\n如果目标包含“学完/掌握/精通/冲刺”等完成型意图，且材料足够，至少使用每日可用时间的 80%。\n学习任务时长不足时，用复习、练习、输出任务或自测补足，而不是留下大段空闲。\n所有 mapped units 都必须进入某个二级任务；可合并相近单元，但 description 里要说明覆盖内容。\n每天任务要具体可执行，包含可检查产出，例如公式默写、例题练习、对比表、错题回顾或口头复述。\n最后一天必须安排综合 quiz/test；quiz/test 必须是当天最后一个二级任务。\n每个 subtask 的 citation_chunk_ids 必须来自 mapped units，不能留空。\ngoal_text: 我要两天学完计网这门课的第七章节，今天是2026年7月12日\ndate_range: 2026-07-12 to 2026-07-13\ndaily_available_minutes: 180\nexpected_material_ids: mat_1fbc7d6e822e4f8b97ebe60e622e6f77\nmapped_batches: [{'units': [{'topic': '物理层概述与功能', 'summary': '物理层位于网络体系结构最底层，实现二进制数据与信号之间的转换（编码/调制发送，接收解调/解码）。主要功能包括：机械特性、电气特性、功能特性、规程特性。', 'difficulty': 'easy', 'estimated_minutes': 15, 'related_material_ids': ['mat_1fbc7d6e822e4f8b97ebe60e622e6f77'], 'citation_chunk_ids': ['chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000002', 'chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000003']}, {'topic': '物理层协议示例：IEEE802.3 10BaseT与RJ45', 'summary': '以IEEE802.3 10BaseT为例，数据率10Mbps，双绞线介质，星形拓扑。RJ45接口机械特性，Manchester编码电气特性（2.5V/-2.5V），功能特性：1、2针发送，3、6针接收，全双工通信。', 'difficulty': 'medium', 'estimated_minutes': 20, 'related_material_ids': ['mat_1fbc7d6e822e4f8b97ebe60e622e6f77'], 'citation_chunk_ids': ['chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000004']}, {'topic': '信息、数据、信号与码元', 'summary': '信息是人类知识的表征；数据是信息二进制载体；信号是数据的电平或电磁波表示；码元是基本信号单位，波特率表示码元速率。模拟信号连续变化，数字信号离散电平。信道分类：狭义物理链路，广义整个路径；模拟信道传输连续电磁波，数字信道传输离散脉冲。模拟通信信道利用率高但质量差，数字通信抗干扰性强但利用率较低。数据通信基础知识：带宽（Hz）、数据率（bps）。', 'difficulty': 'easy', 'estimated_minutes': 15, 'related_material_ids': ['mat_1fbc7d6e822e4f8b97ebe60e622e6f77'], 'citation_chunk_ids': ['chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000006', 'chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000007', 'chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000008', 'chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000009', 'chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000010']}, {'topic': '信道容量：奈奎斯特与香农公式', 'summary': '信号失真原因（码间串扰）：码元速率过高、距离过远、介质差、噪声干扰。无噪声信道最大数据率用奈奎斯特公式：C=2B log2(L)（B带宽，L信号级数）。噪声信道用香农公式：C=B log2(1+S/N)（S/N信噪比，dB=10lg(S/N)）。注意公式需人工复核（标记<!-- formula-not-decoded -->）。', 'difficulty': 'hard', 'estimated_minutes': 25, 'related_material_ids': ['mat_1fbc7d6e822e4f8b97ebe60e622e6f77'], 'citation_chunk_ids': ['chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000011', 'chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000012']}, {'topic': '数字数据编码技术', 'summary': '常见编码方式：NRZ-L（不归零编码）、NRZI（不归零反向编码）、曼彻斯特编码（Manchester）、差分曼\n...<truncated>",
    "status": "ok",
    "elapsed_seconds": 15.127,
    "output": {
      "title": "计算机网络",
      "tasks": [
        {
          "title": "计算机网络",
          "task_date": "2026-07-12",
          "sort_order": 1,
          "subtasks": [
            {
              "title": "物理层概述与物理层协议示例",
              "subtask_type": "learn",
              "description": "学习物理层功能、IEEE802.3 10BaseT与RJ45接口",
              "related_material_ids": [
                "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
              ],
              "estimated_minutes": 35,
              "citation_chunk_ids": [
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000002",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000003",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000004"
              ],
              "sort_order": 1
            },
            {
              "title": "信息、数据、信号与码元",
              "subtask_type": "learn",
              "description": "学习信息、数据、信号、码元概念及信道分类",
              "related_material_ids": [
                "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
              ],
              "estimated_minutes": 15,
              "citation_chunk_ids": [
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000006",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000007",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000008",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000009",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000010"
              ],
              "sort_order": 2
            },
            {
              "title": "数字数据编码技术",
              "subtask_type": "learn",
              "description": "学习NRZ-L、NRZI、曼彻斯特、差分曼彻斯特编码",
              "related_material_ids": [
                "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
              ],
              "estimated_minutes": 20,
              "citation_chunk_ids": [
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000014"
              ],
              "sort_order": 3
            },
            {
              "title": "复习物理层基本概念与编码",
              "subtask_type": "review",
              "description": "默写四种编码波形图并口头复述物理层特性",
              "related_material_ids": [
                "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
              ],
              "estimated_minutes": 20,
              "citation_chunk_ids": [
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000002",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000003",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000004",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000006",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000007",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000014"
              ],
              "sort_order": 4
            },
            {
              "title": "教学内容与章节结构预习",
              "subtask_type": "learn",
              "description": "了解本章内容框架（7.1-7.7）",
              "related_material_ids": [
                "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
              ],
              "estimated_minutes": 5,
              "citation_chunk_ids": [
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000000",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000001",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000005"
              ],
              "sort_order": 5
            }
          ]
        },
        {
          "title": "计算机网络",
          "task_date": "2026-07-13",
          "sort_order": 2,
          "subtasks": [
            {
              "title": "信道容量：奈奎斯特与香农公式",
              "subtask_type": "learn",
              "description": "学习奈奎斯特公式C=2B log2(L)和香农公式C=B log2(1+S/N)及其应用",
              "related_material_ids": [
                "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
              ],
              "estimated_minutes": 25,
              "citation_chunk_ids": [
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000011",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000012"
              ],
              "sort_order": 1
            },
            {
              "title": "练习信道容量计算",
              "subtask_type": "review",
              "description": "完成奈奎斯特和香农公式的计算题练习",
              "related_material_ids": [
                "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
              ],
              "estimated_minutes": 25,
              "citation_chunk_ids": [
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000011",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000012"
              ],
              "sort_order": 2
            },
            {
              "title": "综合分析练习题",
              "subtask_type": "review",
              "description": "对比物理层各知识点，做综合应用题",
              "related_material_ids": [
                "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
              ],
              "estimated_minutes": 30,
              "citation_chunk_ids": [
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000002",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000003",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000004",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000006",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000007",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000008",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000009",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000010",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000011",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000012",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000014"
              ],
              "sort_order": 3
            },
            {
              "title": "综合测试",
              "subtask_type": "test",
              "description": "章节综合测试，涵盖所有物理层知识点",
              "related_material_ids": [
                "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
              ],
              "estimated_minutes": 60,
              "citation_chunk_ids": [
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000000",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000001",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000002",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000003",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000004",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000005",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000006",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000007",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000008",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000009",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000010",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000011",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000012",
                "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000014"
              ],
              "sort_order": 4
            }
          ]
        }
      ],
      "citation_chunk_ids": [
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000000",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000001",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000002",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000003",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000004",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000005",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000006",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000007",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000008",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000009",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000010",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000011",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000012",
        "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000014"
      ]
    }
  }
]
```

## 抽取出的知识单元

```json
[
  {
    "topic": "物理层概述与功能",
    "summary": "物理层位于网络体系结构最底层，实现二进制数据与信号之间的转换（编码/调制发送，接收解调/解码）。主要功能包括：机械特性、电气特性、功能特性、规程特性。",
    "difficulty": "easy",
    "estimated_minutes": 15,
    "related_material_ids": [
      "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
    ],
    "citation_chunk_ids": [
      "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000002",
      "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000003"
    ]
  },
  {
    "topic": "物理层协议示例：IEEE802.3 10BaseT与RJ45",
    "summary": "以IEEE802.3 10BaseT为例，数据率10Mbps，双绞线介质，星形拓扑。RJ45接口机械特性，Manchester编码电气特性（2.5V/-2.5V），功能特性：1、2针发送，3、6针接收，全双工通信。",
    "difficulty": "medium",
    "estimated_minutes": 20,
    "related_material_ids": [
      "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
    ],
    "citation_chunk_ids": [
      "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000004"
    ]
  },
  {
    "topic": "信息、数据、信号与码元",
    "summary": "信息是人类知识的表征；数据是信息二进制载体；信号是数据的电平或电磁波表示；码元是基本信号单位，波特率表示码元速率。模拟信号连续变化，数字信号离散电平。信道分类：狭义物理链路，广义整个路径；模拟信道传输连续电磁波，数字信道传输离散脉冲。模拟通信信道利用率高但质量差，数字通信抗干扰性强但利用率较低。数据通信基础知识：带宽（Hz）、数据率（bps）。",
    "difficulty": "easy",
    "estimated_minutes": 15,
    "related_material_ids": [
      "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
    ],
    "citation_chunk_ids": [
      "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000006",
      "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000007",
      "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000008",
      "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000009",
      "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000010"
    ]
  },
  {
    "topic": "信道容量：奈奎斯特与香农公式",
    "summary": "信号失真原因（码间串扰）：码元速率过高、距离过远、介质差、噪声干扰。无噪声信道最大数据率用奈奎斯特公式：C=2B log2(L)（B带宽，L信号级数）。噪声信道用香农公式：C=B log2(1+S/N)（S/N信噪比，dB=10lg(S/N)）。注意公式需人工复核（标记<!-- formula-not-decoded -->）。",
    "difficulty": "hard",
    "estimated_minutes": 25,
    "related_material_ids": [
      "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
    ],
    "citation_chunk_ids": [
      "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000011",
      "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000012"
    ]
  },
  {
    "topic": "数字数据编码技术",
    "summary": "常见编码方式：NRZ-L（不归零编码）、NRZI（不归零反向编码）、曼彻斯特编码（Manchester）、差分曼彻斯特编码（Differential Manchester）。",
    "difficulty": "medium",
    "estimated_minutes": 20,
    "related_material_ids": [
      "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
    ],
    "citation_chunk_ids": [
      "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000014"
    ]
  },
  {
    "topic": "教学内容与章节结构",
    "summary": "资料涵盖教学内容要求：物理层功能、数据通信基础（Nyquist/Shannon公式）、调制/编码/复用方法、HUB功能、物理层安全隐患。内容目录包括7.1至7.7。该单元为综述性质，具体知识已在其他单元展开。",
    "difficulty": "easy",
    "estimated_minutes": 5,
    "related_material_ids": [
      "mat_1fbc7d6e822e4f8b97ebe60e622e6f77"
    ],
    "citation_chunk_ids": [
      "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000000",
      "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000001",
      "chk_1fbc7d6e822e4f8b97ebe60e622e6f77_000005"
    ]
  }
]
```

## 最终预览计划

未生成 preview。


## 保存结果

未保存计划。


## 错误堆栈

```text
Traceback (most recent call last):
  File "C:\Users\50754\AppData\Local\Temp\course_nexus_net_chap7_after_quality_report.py", line 206, in main
    preview = preview_study_plan(
              ^^^^^^^^^^^^^^^^^^^
  File "D:\Projects\CourseNexus\backend\app\modules\study_plans\service.py", line 114, in preview_study_plan
    validate_preview(preview=preview, scoped_material_ids=expected_material_ids)
  File "D:\Projects\CourseNexus\backend\app\modules\study_plans\planner.py", line 72, in validate_preview
    raise _invalid_generation("每日任务时长利用不足")
app.core.errors.CourseNexusError: 每日任务时长利用不足

```


## 本次测试结论

- 已读取到 `study_plan_parser` 与 `study_plan_generator` 的真实模型配置，并完成真实模型调用。
- Parser 调用成功，正确从自然语言中解析出 `2026-07-12` 到 `2026-07-13` 的两天范围；由于用户未说明每日可用时长，`daily_available_minutes` 保持未解析，并进入 `unresolved_fields`。
- 测试脚本为了继续生成 preview，按测试约定补入每日 `180` 分钟。
- 资料解析成功入库，但 Docling/RapidOCR 对 PDF 后半部分出现内存不足，最终只得到 `15` 个 chunk，覆盖页码为 `2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 32`。
- Generator map 调用成功，抽取出 `6` 个知识单元：物理层概述与功能、10BaseT/RJ45、信息/数据/信号/码元、奈奎斯特与香农公式、数字数据编码技术、教学内容与章节结构。
- Generator reduce 调用成功，候选计划第 1 天合计 `95` 分钟，第 2 天合计 `140` 分钟，并把最终综合测试放在最后一天最后一个任务。
- 后端实际 preview 未返回成功结果，因为 `validate_preview()` 检查到第 1 天 `95` 分钟低于每日 `180` 分钟的最低利用率阈值 `108` 分钟，抛出 `每日任务时长利用不足`。
- 因 preview 校验失败，本次没有进入保存阶段，数据库中未保存学习计划。
## 初步观察

- 报告未写入任何明文 API Key。
