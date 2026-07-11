# 计网第七章物理层真实模型学习计划测试报告

- 测试日期：2026-07-12
- 自然语言输入：我要两天学完计网这门课的第七章节，今天是2026年7月12日
- 资料：`D:\大二下课程\计算机网络\课件\Chap7 物理层.pdf`
- 说明：密钥只用于本次模型调用，报告不记录密钥值；API 响应中的 access_token 已脱敏。

## 模型配置摘要

```json
{
  "env": {
    "STUDY_PLAN_PARSER_API_KEY": "<redacted>",
    "STUDY_PLAN_PARSER_BASE_URL": {
      "configured": true,
      "source": ".env.example"
    },
    "STUDY_PLAN_PARSER_MODEL": {
      "configured": true,
      "source": ".env.example"
    },
    "STUDY_PLAN_GENERATOR_API_KEY": "<redacted>",
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
  "goal_text": "我要两天学完计网这门课的第七章节",
  "start_date": "2026-07-12",
  "end_date": "2026-07-13",
  "daily_available_minutes": 180,
  "material_scope": {
    "include_all_parsed_materials": true,
    "material_ids": []
  }
}
```

## 资料解析输出

```json
{
  "material_id": "mat_42bc4a052a8647dd9d9c26d3cf9bdb26",
  "name": "Chap7 物理层.pdf",
  "material_type": "pdf",
  "parse_status": "parsed",
  "parse_error": null,
  "chunk_count": 48,
  "chunks": [
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000000",
      "chunk_index": 0,
      "heading": "第七章 物理层 Physical Layer",
      "page": "1",
      "text": "网络空间安全学院 韩东岐 2025年6月"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000001",
      "chunk_index": 1,
      "heading": " 7.1 物理层概述",
      "page": "2",
      "text": "-  7.2 数据通信的基础知识\n-  7.3 传输介质\n-  7.4 调制技术和编码技术\n-  7.5 复用技术\n-  7.6 物理层互连设备\n-  7.7 物理层的安全隐患"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000002",
      "chunk_index": 2,
      "heading": "教学内容及要求",
      "page": "3",
      "text": "-  掌握物理层的功能和主要概念\n-  掌握数据通信的基本概念和理论基础：\n-  Nyquest 公式和 Shannon 公式\n-  掌握常用的调制、编码和复用的方法要点\n-  了解 HUB 的功能\n-  了解物理层的安全隐患"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000003",
      "chunk_index": 3,
      "heading": "物理层的位置和基本功能",
      "page": "4",
      "text": "-  网络体系结构的最底层，实现真正的数据传输\n-  将二进制数据编码或调制成信号，发送到传输介质 ( 传输媒体 )\n-  从传输介质接收信号，转换成二进制数据"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000004",
      "chunk_index": 4,
      "heading": "物理层的主要功能",
      "page": "5",
      "text": "-  规定了与传输介质的接口的特性\n-  机械特性：规定接口所用接线器的形状和尺寸、引 线数目和排列等\n-  电气特性：规定在接口电缆的各条线上的电压范围\n-  功能特性：规定接口电缆的某条线出现某一电平的 含义\n-  规程特性：规定各种可能事件的出现顺序"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000005",
      "chunk_index": 5,
      "heading": "物理层协议示例",
      "page": "6",
      "text": "-  IEEE802.3 ， 10BaseT\n-  数据率 10Mbps ，传输介质为双绞线，拓扑结构为星形\n-  物理接口的特性\n-  机械特性： RJ45 接口\n-  电气特性：\n-  Manchester 编码\n-  电平： 2.5v ， -2.5v\n-  功能特性：\n-  一对线发送（ 1,2 针）、一对线接收（ 3,6 针）\n-  全双工通信\nRJ-45 Female\nRJ-45 Male"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000006",
      "chunk_index": 6,
      "heading": "主要内容",
      "page": "7",
      "text": "-  7.1 物理层概述\n-  7.2 数据通信的基础知识\n-  7.3 传输介质\n-  7.4 调制技术和编码技术\n-  7.5 复用技术\n-  7.6 物理层互连设备\n-  7.7 物理层的安全隐患"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000007",
      "chunk_index": 7,
      "heading": " 信息、数据与信号",
      "page": "9",
      "text": "-  信息：人类知识的表征，通信的目的就是传输信息。 信息的载体包括数字、文字、语音、图形或图像。\n-  数据：承载信息的实体，以二进制的形式在计算机 系统中处理。\n-  信号：数据的电平或电磁波形式表示，在传输介质 上传播。\n-  码元：基本信号单位\n-  码元的速率称为波特率 (Baud)"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000008",
      "chunk_index": 8,
      "heading": "模拟信号与数字信号",
      "page": "10",
      "text": "-  模拟信号 (Analog Signal) ：信号的幅度随时间 连续变化。\n-  数字信号 (Digital Signal) ：离散的电平值"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000009",
      "chunk_index": 9,
      "heading": "信道：信号的通道",
      "page": "11",
      "text": "-  狭义的信道指的是连接两个设备之间的传输介质，即 物理链路（计算机网络课程范畴使用）\n-  广义的信道指的是信号传输的整个路径，中间可能经 过多个设备，如因特网上位于不同城市的两台计算机 之间的通路\n-  模拟信道以连续的电磁波形式来传输数据； 数字信道以离散的数字脉冲形式传输数据"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000010",
      "chunk_index": 10,
      "heading": "模拟通信与数字通信",
      "page": "12",
      "text": "-  模拟通信：信道中传输的是模拟信号，如有线电 视系统中的通信\n-  信道利用率高，但传输质量差\n-  数字通信：信道中传输的是数字信号，如因特网 上的通信\n-  衰减低，抗干扰性强\n-  信道利用率较低\n-  模拟信道上传输的不一定是模拟数据，反之亦然"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000011",
      "chunk_index": 11,
      "heading": "数据率与带宽",
      "page": "13",
      "text": "-  带宽：信道传输电磁波信号的频率范围（可通 过的最高频率 -最低频率），单位： Hz\n-  数据率：信道的最大传输速率，单位： bps"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000012",
      "chunk_index": 12,
      "heading": "最大数据率（信道容量）",
      "page": "14",
      "text": "-  为什么信道容量有上限？\n-  信号失真（码间串扰）\n-  码元传输速度过高\n-  信号传输距离过远\n-  传输介质质量差\n-  噪声干扰\n-  如何计算最大数据率（极限信道容量）？\n-  奈奎斯特（ Nyquist ）公式：用于无噪声信道\n-  香农（ Shannon ）公式：用于噪声信道"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000013",
      "chunk_index": 13,
      "heading": "最大数据率（信道容量）公式",
      "page": "15",
      "text": "-  奈奎斯特（ Nyquist ）公式：用于无噪声信道\n<!-- formula-not-decoded -->\n-  C ：最大数据率， B ：带宽， L ：信号级数\n-  香农（ Shannon ）公式：用于噪声信道\n<!-- formula-not-decoded -->\n-  S/N ：信噪比\n-  单位为分贝， dB 值 =10 × lg(S/N)"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000014",
      "chunk_index": 14,
      "heading": "主要内容",
      "page": "16",
      "text": "-  7.1 物理层概述\n-  7.2 数据通信的基础知识\n-  7.3 传输介质\n-  7.4 调制技术和编码技术\n-  7.5 复用技术\n-  7.6 物理层互连设备\n-  7.7 物理层的安全隐患"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000015",
      "chunk_index": 15,
      "heading": "传输介质及分类",
      "page": "17",
      "text": "-  也称为传输媒体\n-  有线介质\n-  双绞线、同轴电缆、光纤\n-  无线介质\n-  无线电（ RF ）、微波、卫星"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000016",
      "chunk_index": 16,
      "heading": "电磁波的频谱",
      "page": "19",
      "text": "-  两根互相绝缘的铜线互相缠绕构成\n-  可传输模拟信号和数字信号\n-  主要应用\n-  固定电话的用户线\n-  计算机的网线"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000017",
      "chunk_index": 17,
      "heading": " 两类同轴电缆",
      "page": "20",
      "text": "-  阻抗 50Ω ，传输数字信号，用于计算机联网\n-  阻抗 75Ω ，传输模拟信号，有线电视电缆"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000018",
      "chunk_index": 18,
      "heading": "光纤",
      "page": "21",
      "text": "-  用于传输数字信号\n-  高带宽\n-  抗干扰\n-  低衰减、传输距离长\n-  重量轻"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000019",
      "chunk_index": 19,
      "heading": "基站覆盖的无线电区域",
      "page": "22",
      "text": "-  全方位传输\n-  可以穿透建筑物\n-  时延长\n-  抗干扰能力差"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000020",
      "chunk_index": 20,
      "heading": "ISM 频段",
      "page": "23",
      "text": "-  Industrial, Scientific, Medical\n-  不必申请\n-  在 WLAN 、蓝牙中广泛使用"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000021",
      "chunk_index": 21,
      "heading": "地面微波",
      "page": "24",
      "text": "-  直线传输\n-  长距离传输时需要中继器（ Repeater ）\n-  不能穿透建筑物\n-  易受天气影响"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000022",
      "chunk_index": 22,
      "heading": "主要内容",
      "page": "26",
      "text": "-  7.1 物理层概述\n-  7.2 数据通信的基础知识\n-  7.3 传输介质\n-  7.4 调制技术和编码技术\n-  7.5 复用技术\n-  7.6 物理层互连设备\n-  7.7 物理层的安全隐患"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000023",
      "chunk_index": 23,
      "heading": "模拟信号的特征",
      "page": "28",
      "text": "-  振幅、频率、相位"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000024",
      "chunk_index": 24,
      "heading": "多级调制方法：正交振幅调制 QAM",
      "page": "30",
      "text": "-  调幅和调相相结合\n-  一个码元表示多位数据"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000025",
      "chunk_index": 25,
      "heading": "数字数据编码技术",
      "page": "32",
      "text": "NRZ-L\n不归零编码\n不归零反向编码 NRZI\n曼彻斯特编码 Manchester\nDifferential manchester\n差分曼彻斯特"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000026",
      "chunk_index": 26,
      "heading": "脉冲编码调制 PCM",
      "page": "33",
      "text": "-  将模拟信号转换成数字信号"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000027",
      "chunk_index": 27,
      "heading": "主要内容",
      "page": "35",
      "text": "-  7.1 物理层概述\n-  7.2 数据通信的基础知识\n-  7.3 传输介质\n-  7.4 调制技术和编码技术\n-  7.5 复用技术\n-  7.6 物理层互连设备\n-  7.7 物理层的安全隐患"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000028",
      "chunk_index": 28,
      "heading": "复用的概念",
      "page": "36",
      "text": "-  多路信号共享一条信道\n- (a) 不使用复用技术\n- (b) 使用复用技术"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000029",
      "chunk_index": 29,
      "heading": " 按照不同的频率划分子信道，用于模拟信号复用",
      "page": "37",
      "text": "37\n页"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000030",
      "chunk_index": 30,
      "heading": "时分复用 TDM",
      "page": "39",
      "text": "-  按照时间片来划分子信道，用于数字信号复用\n-  所有用户在不同的时间占用同样的频带宽度\n同步时分复用"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000031",
      "chunk_index": 31,
      "heading": "同步时分复用示例： E1 帧",
      "page": "40",
      "text": "-  应用于电话骨干网，数字话音传输"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000032",
      "chunk_index": 32,
      "heading": "同步时分复用的不足",
      "page": "41",
      "text": "-  计算机数据的突发性易导致信道资源浪费"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000033",
      "chunk_index": 33,
      "heading": "主要内容",
      "page": "43",
      "text": "-  7.1 物理层概述\n-  7.2 数据通信的基础知识\n-  7.3 传输介质\n-  7.4 调制技术和编码技术\n-  7.5 复用技术\n-  7.6 物理层互连设备\n-  7.7 物理层的安全隐患"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000034",
      "chunk_index": 34,
      "heading": "网络互连设备",
      "page": "44",
      "text": "应用层\n传输层\n网络层\n数据链路层\n物理层"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000035",
      "chunk_index": 35,
      "heading": "互联设备",
      "page": "44",
      "text": "网 关\n路由器\n网桥 / 交换机\nHub/ 中继器"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000036",
      "chunk_index": 36,
      "heading": "地址",
      "page": "44",
      "text": "端口号等\nIPv4/ IPv6 地址\nMAC 地址\n连接器、接插板"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000037",
      "chunk_index": 37,
      "heading": "物理层互连设备：中继器（ Repeater ）",
      "page": "45",
      "text": "-  连接两个 LAN 网段 (Segment)\n-  将信号再生，以便传输得更远"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000038",
      "chunk_index": 38,
      "heading": "物理层互连设备： HUB （集线器）",
      "page": "46",
      "text": "-  多端口中继器\n-  将主机连接起来组成 LAN\n-  物理拓扑结构为星形\n-  逻辑拓扑结构为总线形\n-  将信号放大再生\n-  广播信道：从一个端口收到 的数据将转发到所有其他 端口\n-  共享式 LAN"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000039",
      "chunk_index": 39,
      "heading": "主要内容",
      "page": "47",
      "text": "-  7.1 物理层概述\n-  7.2 数据通信的基础知识\n-  7.3 传输介质\n-  7.4 调制技术和编码技术\n-  7.5 复用技术\n-  7.6 物理层互连设备\n-  7.7 物理层的安全隐患"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000040",
      "chunk_index": 40,
      "heading": "数据截获",
      "page": "48",
      "text": "-  从中继器上截获\n-  从网卡截获\n-  从交换机截获\n-  从电力系统捕获按键产生的电磁脉冲\n-  利用光线反射捕获键盘输入"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000041",
      "chunk_index": 41,
      "heading": "物理层小结",
      "page": "49",
      "text": "-  物理层的功能\n-  数据通信的基本概念和理论\n-  香农公式和奈奎斯特公式\n-  常用的传输介质的特点和应用场合\n-  调制、编码、复用的概念\n-  中继器和 HUB 的功能"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000042",
      "chunk_index": 42,
      "heading": "一次 Web 请求的过程",
      "page": "50",
      "text": "-  贯穿完整的五层体系结构\n-  应用层、传输层、网络层、数据链路层和 物理层\n-  目标：综合理解网络的整体工作过程、 相关协议的功能及要点\n-  示例场景：访问 www.baidu.com"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000043",
      "chunk_index": 43,
      "heading": "第一步：连接到因特网（ 1 ）",
      "page": "52",
      "text": "-  笔记本电脑首先要获得上网 参数： IP 地址、路由器地址 、 DNS 服务器的 IP 地址\n-  使用 DHCP\n-  DHCP 请求：\n- 封装在 UDP 数据报\n-  IP 包  以太网帧\n-  以太网帧在 LAN 上广播 （目的 MAC 地址为 FFFF-FF-FF-FF-FF)\n-  DHCP 服务器收到以太网帧，解封： IP 包  UDP 数据报  DHCP 请求"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000044",
      "chunk_index": 44,
      "heading": "第一步：连接到因特网（ 2 ）",
      "page": "53",
      "text": "-  DHCP 服务器返回 DHCP ACK ，包含所 请求的上网相关参数\n-  DHCP 服务器将 DHCP ACK 封装成帧， 通过 LAN 交换机转发 给笔记本电脑\n-  解封， DHCP 客户收到 DHCP ACK\n客户端获得IP地址，获知子网掩码、路由器的IP地址、 DNS服务器的IP地址"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000045",
      "chunk_index": 45,
      "heading": "第二步： ARP",
      "page": "54",
      "text": "-  客户端获知路由器接口的 MAC 地址，可以发送包含 DNS 请求的帧\n-  发送 HTTP 请求之前，客户端 需要获知 www.baidu.com 对 应的 IP 地址  使用 DNS\n-  解析器产生 DNS 请求，封装：  UDP 数据报  IP 包  以太 网帧\n-  要把帧发送给路由器，需要 MAC 地址  使用 ARP\n-  客户端广播 ARP 请求，路由 器收到后发送 ARP 应答，包 含自己接口网卡的 MAC 地址"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000046",
      "chunk_index": 46,
      "heading": "第四步：建立 TCP 连接",
      "page": "56",
      "text": "TCP 连接建"
    },
    {
      "chunk_id": "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000047",
      "chunk_index": 47,
      "heading": "版权说明",
      "page": "58",
      "text": "-  本讲义中有部分图片来源于下列教材所附讲义：\n-  Andrew S. Tanenbaum, Computer Networks, Fourth Edition, 清华大学出版社（影印版）， 2004 ，引用时标 记为 [Tanenbaum] ;\n-  谢希仁，计算机网络，第五版，电子工业出版社， 2008 年 1 月 , 引用时标记为 [ 谢 ] ；\n-  James F. Kurose, Keith W. Ross ， Computer Networking: A Top Down Approach ， 7 th  Edition, Pearson/Addison Wesley, April 2016 ，引用时标记为 [Kurose];\n-  Behrouz A. Forouzan ， Data Communications and Networking ， Fourth Edition, McGraw-Hill  Higher Education, 2007 年 1 月，引用时标记为 [Forouzan]"
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
    "content_excerpt": "{\n  \"goal_text\": \"我要两天学完计网这门课的第七章节\",\n  \"start_date\": \"2026-07-12\",\n  \"end_date\": null,\n  \"daily_available_minutes\": null,\n  \"preference\": null,\n  \"material_scope\": {\n    \"include_all_parsed_materials\": true,\n    \"material_ids\": []\n  },\n  \"unresolved_fields\": [\"end_date\", \"daily_available_minutes\", \"preference\"]\n}"
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
    "content_excerpt": "{\n  \"units\": [\n    {\n      \"topic\": \"物理层概述与功能\",\n      \"summary\": \"物理层是网络体系结构的最底层，负责将二进制数据编码成信号并通过传输介质发送，以及接收信号并转换为二进制数据。其功能包括定义机械、电气、功能和规程特性。\",\n      \"difficulty\": \"easy\",\n      \"estimated_minutes\": 20,\n      \"related_material_ids\": [\"mat_42bc4a052a8647dd9d9c26d3cf9bdb26\"],\n      \"citation_chunk_ids\": [\"chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000003\", \"chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000004\"]\n    },\n    {\n      \"topic\": \"数据通信基础知识\",\n      \"summary\": \"包括信息、数据、信号、码元的概念，模拟与数字信号，信道分类，模拟通信与数字通信的区别，数据率与带宽，以及信道容量公式（奈奎斯特定理和香农定理）。\",\n      \"difficulty\": \"medium\",\n      \"estimated_minutes\": 30,\n      \"related_material_ids\": [\"mat_42bc4a052a8647dd9d9c26d3cf9bdb26\"],\n      \"citation_chunk_ids\": [\"chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000007\", \"chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000008\", \"chk_42bc4a05"
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
    "content_excerpt": "{\n  \"title\": \"计算机网路第七章物理层学习计划\",\n  \"tasks\": [\n    {\n      \"title\": \"第一天：物理层基础与数据通信\",\n      \"task_date\": \"2026-07-12\",\n      \"sort_order\": 1,\n      \"subtasks\": [\n        {\n          \"title\": \"物理层概述与功能\",\n          \"subtask_type\": \"learn\",\n          \"description\": \"物理层是网络体系结构的最底层，负责将二进制数据编码成信号并通过传输介质发送，以及接收信号并转换为二进制数据。其功能包括定义机械、电气、功能和规程特性。\",\n          \"related_material_ids\": [\"mat_42bc4a052a8647dd9d9c26d3cf9bdb26\"],\n          \"estimated_minutes\": 20,\n          \"citation_chunk_ids\": [\"chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000003\", \"chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000004\"],\n          \"sort_order\": 1\n        },\n        {\n          \"title\": \"数据通信基础知识\",\n          \"subtask_type\": \"learn\",\n          \"description\": \"包括信息、数据、信号、码元的概念，模拟与数字信号，信道分类，模拟通信与数字通信的区别，数据率与带宽，以及信道容量公式（奈奎斯特定理和香农定理）。\",\n       "
  }
]
```

## 真实模型结构化输出

```json
[
  {
    "provider": "study_plan_parser",
    "schema": "StudyPlanParsedConfig",
    "prompt_excerpt": "你是 CourseNexus 的学习计划配置解析器。\n只从用户目标中提取可编辑的学习计划字段，不创建计划，不编造无法确定的信息。\n无法可靠确定的字段填 null，并把字段名加入 unresolved_fields。\n课程名称：计算机网络\n用户目标：我要两天学完计网这门课的第七章节，今天是2026年7月12日\n资料范围：{'include_all_parsed_materials': True, 'material_ids': []}",
    "result": {
      "goal_text": "我要两天学完计网这门课的第七章节",
      "start_date": "2026-07-12",
      "end_date": null,
      "daily_available_minutes": null,
      "preference": null,
      "material_scope": {
        "include_all_parsed_materials": true,
        "material_ids": []
      },
      "unresolved_fields": [
        "end_date",
        "daily_available_minutes",
        "preference"
      ]
    }
  },
  {
    "provider": "study_plan_generator",
    "schema": "PlanBatchExtraction",
    "prompt_excerpt": "你是 CourseNexus 的学习计划材料分析器。\n请把本批资料提炼为可排入学习计划的知识单元。\ngoal_text: 我要两天学完计网这门课的第七章节\ndate_range: 2026-07-12 to 2026-07-13\ndaily_available_minutes: 180\nmaterial_ids: mat_42bc4a052a8647dd9d9c26d3cf9bdb26\nchunks:\nchunk_id=chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000000 material_id=mat_42bc4a052a8647dd9d9c26d3cf9bdb26 heading=第七章 物理层 Physical Layer text=网络空间安全学院 韩东岐 2025年6月\nchunk_id=chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000001 material_id=mat_42bc4a052a8647dd9d9c26d3cf9bdb26 heading= 7.1 物理层概述 text=-  7.2 数据通信的基础知识\n-  7.3 传输介质\n-  7.4 调制技术和编码技术\n-  7.5 复用技术\n-  7.6 物理层互连设备\n-  7.7 物理层的安全隐患\nchunk_id=chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000002 material_id=mat_42bc4a052a8647dd9d9c26d3cf9bdb26 heading=教学内容及要求 text=-  掌握物理层的功能和主要概念\n-  掌握数据通信的基本概念和理论基础：\n-  Nyquest 公式和 Shannon 公式\n-  掌握常用的调制、编码和复用的方法要点\n-  了解 HUB 的功能\n-  了解物理层的安全隐患\nchunk_id=chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000003 material_id=mat_42bc4a052a8647dd9d9c26d3cf9bdb26 heading=物理层的位置和基本功能 text=-  网络体系结构的最底层，实现真正的数据传输\n-  将二进制数据编码或调制成信号，发送到传输介质 ( 传输媒体 )\n-  从传输介质接收信号，转换成二进制数据\nchunk_id=chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000004 material_id=mat_42bc4a052a8647dd9d9c26d3cf9bdb26 heading=物理层的主要功能 text=-  规定了与传输介质的接口的特性\n-  机械特性：规定接口所用接线器的",
    "result": {
      "units": [
        {
          "topic": "物理层概述与功能",
          "summary": "物理层是网络体系结构的最底层，负责将二进制数据编码成信号并通过传输介质发送，以及接收信号并转换为二进制数据。其功能包括定义机械、电气、功能和规程特性。",
          "difficulty": "easy",
          "estimated_minutes": 20,
          "related_material_ids": [
            "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
          ],
          "citation_chunk_ids": [
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000003",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000004"
          ]
        },
        {
          "topic": "数据通信基础知识",
          "summary": "包括信息、数据、信号、码元的概念，模拟与数字信号，信道分类，模拟通信与数字通信的区别，数据率与带宽，以及信道容量公式（奈奎斯特定理和香农定理）。",
          "difficulty": "medium",
          "estimated_minutes": 30,
          "related_material_ids": [
            "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
          ],
          "citation_chunk_ids": [
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000007",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000008",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000009",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000010",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000011",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000012",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000013"
          ]
        },
        {
          "topic": "传输介质",
          "summary": "传输介质包括有线介质（双绞线、同轴电缆、光纤）和无线介质（无线电、微波、卫星）。掌握它们的特点和应用场合。",
          "difficulty": "easy",
          "estimated_minutes": 20,
          "related_material_ids": [
            "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
          ],
          "citation_chunk_ids": [
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000015",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000016",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000017",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000018",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000019",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000020",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000021"
          ]
        },
        {
          "topic": "调制技术和编码技术",
          "summary": "模拟信号的特征（振幅、频率、相位），调制方法（如QAM），数字数据编码（NRZ-L、NRZI、曼彻斯特、差分曼彻斯特），以及脉冲编码调制PCM。",
          "difficulty": "medium",
          "estimated_minutes": 30,
          "related_material_ids": [
            "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
          ],
          "citation_chunk_ids": [
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000023",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000024",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000025",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000026"
          ]
        },
        {
          "topic": "复用技术",
          "summary": "复用概念，频分复用（FDM）、时分复用（TDM）及其同步时分复用示例（E1帧），以及同步时分复用的不足。",
          "difficulty": "medium",
          "estimated_minutes": 20,
          "related_material_ids": [
            "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
          ],
          "citation_chunk_ids": [
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000028",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000029",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000030",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000031",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000032"
          ]
        },
        {
          "topic": "物理层互连设备",
          "summary": "物理层互连设备包括中继器（Repeater）和集线器（HUB）。中继器连接两个网段并再生信号；HUB是多端口中继器，组成广播型LAN。",
          "difficulty": "easy",
          "estimated_minutes": 15,
          "related_material_ids": [
            "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
          ],
          "citation_chunk_ids": [
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000034",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000035",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000036",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000037",
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000038"
          ]
        },
        {
          "topic": "物理层的安全隐患",
          "summary": "物理层的安全隐患包括数据截获（从中继器、网卡、交换机、电磁脉冲等）。",
          "difficulty": "easy",
          "estimated_minutes": 10,
          "related_material_ids": [
            "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
          ],
          "citation_chunk_ids": [
            "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000040"
          ]
        }
      ],
      "citation_chunk_ids": [
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000003",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000004",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000007",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000008",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000009",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000010",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000011",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000012",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000013",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000015",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000016",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000017",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000018",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000019",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000020",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000021",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000023",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000024",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000025",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000026",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000028",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000029",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000030",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000031",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000032",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000034",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000035",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000036",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000037",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000038",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000040"
      ]
    }
  },
  {
    "provider": "study_plan_generator",
    "schema": "StudyPlanReduction",
    "prompt_excerpt": "你是 CourseNexus 的学习计划排程器。\n请把所有材料单元归并为日期连续、可执行的单课程学习计划预览。\ngoal_text: 我要两天学完计网这门课的第七章节\ndate_range: 2026-07-12 to 2026-07-13\ndaily_available_minutes: 180\nexpected_material_ids: mat_42bc4a052a8647dd9d9c26d3cf9bdb26\nmapped_batches: [{'units': [{'topic': '物理层概述与功能', 'summary': '物理层是网络体系结构的最底层，负责将二进制数据编码成信号并通过传输介质发送，以及接收信号并转换为二进制数据。其功能包括定义机械、电气、功能和规程特性。', 'difficulty': 'easy', 'estimated_minutes': 20, 'related_material_ids': ['mat_42bc4a052a8647dd9d9c26d3cf9bdb26'], 'citation_chunk_ids': ['chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000003', 'chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000004']}, {'topic': '数据通信基础知识', 'summary': '包括信息、数据、信号、码元的概念，模拟与数字信号，信道分类，模拟通信与数字通信的区别，数据率与带宽，以及信道容量公式（奈奎斯特定理和香农定理）。', 'difficulty': 'medium', 'estimated_minutes': 30, 'related_material_ids': ['mat_42bc4a052a8647dd9d9c26d3cf9bdb26'], 'citation_chunk_ids': ['chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000007', 'chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000008', 'chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000009', 'chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000010', 'chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000011', 'chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000012', 'chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000013']}, {'topic': '传输介质', 'summary': '传输介质包括有线介质",
    "result": {
      "title": "计算机网路第七章物理层学习计划",
      "tasks": [
        {
          "title": "第一天：物理层基础与数据通信",
          "task_date": "2026-07-12",
          "sort_order": 1,
          "subtasks": [
            {
              "title": "物理层概述与功能",
              "subtask_type": "learn",
              "description": "物理层是网络体系结构的最底层，负责将二进制数据编码成信号并通过传输介质发送，以及接收信号并转换为二进制数据。其功能包括定义机械、电气、功能和规程特性。",
              "related_material_ids": [
                "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
              ],
              "estimated_minutes": 20,
              "citation_chunk_ids": [
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000003",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000004"
              ],
              "sort_order": 1
            },
            {
              "title": "数据通信基础知识",
              "subtask_type": "learn",
              "description": "包括信息、数据、信号、码元的概念，模拟与数字信号，信道分类，模拟通信与数字通信的区别，数据率与带宽，以及信道容量公式（奈奎斯特定理和香农定理）。",
              "related_material_ids": [
                "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
              ],
              "estimated_minutes": 30,
              "citation_chunk_ids": [
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000007",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000008",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000009",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000010",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000011",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000012",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000013"
              ],
              "sort_order": 2
            },
            {
              "title": "传输介质",
              "subtask_type": "learn",
              "description": "传输介质包括有线介质（双绞线、同轴电缆、光纤）和无线介质（无线电、微波、卫星）。掌握它们的特点和应用场合。",
              "related_material_ids": [
                "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
              ],
              "estimated_minutes": 20,
              "citation_chunk_ids": [
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000015",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000016",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000017",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000018",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000019",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000020",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000021"
              ],
              "sort_order": 3
            },
            {
              "title": "复习第一天内容",
              "subtask_type": "review",
              "description": "复习物理层概述、数据通信基础知识和传输介质，巩固理解。",
              "related_material_ids": [
                "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
              ],
              "estimated_minutes": 30,
              "citation_chunk_ids": [],
              "sort_order": 4
            }
          ]
        },
        {
          "title": "第二天：调制编码、复用与设备",
          "task_date": "2026-07-13",
          "sort_order": 2,
          "subtasks": [
            {
              "title": "调制技术和编码技术",
              "subtask_type": "learn",
              "description": "模拟信号的特征（振幅、频率、相位），调制方法（如QAM），数字数据编码（NRZ-L、NRZI、曼彻斯特、差分曼彻斯特），以及脉冲编码调制PCM。",
              "related_material_ids": [
                "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
              ],
              "estimated_minutes": 30,
              "citation_chunk_ids": [
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000023",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000024",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000025",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000026"
              ],
              "sort_order": 1
            },
            {
              "title": "复用技术",
              "subtask_type": "learn",
              "description": "复用概念，频分复用（FDM）、时分复用（TDM）及其同步时分复用示例（E1帧），以及同步时分复用的不足。",
              "related_material_ids": [
                "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
              ],
              "estimated_minutes": 20,
              "citation_chunk_ids": [
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000028",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000029",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000030",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000031",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000032"
              ],
              "sort_order": 2
            },
            {
              "title": "物理层互连设备",
              "subtask_type": "learn",
              "description": "物理层互连设备包括中继器（Repeater）和集线器（HUB）。中继器连接两个网段并再生信号；HUB是多端口中继器，组成广播型LAN。",
              "related_material_ids": [
                "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
              ],
              "estimated_minutes": 15,
              "citation_chunk_ids": [
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000034",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000035",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000036",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000037",
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000038"
              ],
              "sort_order": 3
            },
            {
              "title": "物理层的安全隐患",
              "subtask_type": "learn",
              "description": "物理层的安全隐患包括数据截获（从中继器、网卡、交换机、电磁脉冲等）。",
              "related_material_ids": [
                "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
              ],
              "estimated_minutes": 10,
              "citation_chunk_ids": [
                "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000040"
              ],
              "sort_order": 4
            },
            {
              "title": "综合复习与自测",
              "subtask_type": "quiz",
              "description": "复习调制编码、复用、设备和安全隐患，完成练习题或自测巩固知识。",
              "related_material_ids": [
                "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
              ],
              "estimated_minutes": 45,
              "citation_chunk_ids": [],
              "sort_order": 5
            }
          ]
        }
      ],
      "citation_chunk_ids": [
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000003",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000004",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000007",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000008",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000009",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000010",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000011",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000012",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000013",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000015",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000016",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000017",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000018",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000019",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000020",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000021",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000023",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000024",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000025",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000026",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000028",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000029",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000030",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000031",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000032",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000034",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000035",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000036",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000037",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000038",
        "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000040"
      ]
    }
  }
]
```

## 模型提炼的知识点

```json
[
  {
    "topic": "物理层概述与功能",
    "summary": "物理层是网络体系结构的最底层，负责将二进制数据编码成信号并通过传输介质发送，以及接收信号并转换为二进制数据。其功能包括定义机械、电气、功能和规程特性。",
    "difficulty": "easy",
    "estimated_minutes": 20,
    "related_material_ids": [
      "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
    ],
    "citation_chunk_ids": [
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000003",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000004"
    ]
  },
  {
    "topic": "数据通信基础知识",
    "summary": "包括信息、数据、信号、码元的概念，模拟与数字信号，信道分类，模拟通信与数字通信的区别，数据率与带宽，以及信道容量公式（奈奎斯特定理和香农定理）。",
    "difficulty": "medium",
    "estimated_minutes": 30,
    "related_material_ids": [
      "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
    ],
    "citation_chunk_ids": [
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000007",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000008",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000009",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000010",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000011",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000012",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000013"
    ]
  },
  {
    "topic": "传输介质",
    "summary": "传输介质包括有线介质（双绞线、同轴电缆、光纤）和无线介质（无线电、微波、卫星）。掌握它们的特点和应用场合。",
    "difficulty": "easy",
    "estimated_minutes": 20,
    "related_material_ids": [
      "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
    ],
    "citation_chunk_ids": [
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000015",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000016",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000017",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000018",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000019",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000020",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000021"
    ]
  },
  {
    "topic": "调制技术和编码技术",
    "summary": "模拟信号的特征（振幅、频率、相位），调制方法（如QAM），数字数据编码（NRZ-L、NRZI、曼彻斯特、差分曼彻斯特），以及脉冲编码调制PCM。",
    "difficulty": "medium",
    "estimated_minutes": 30,
    "related_material_ids": [
      "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
    ],
    "citation_chunk_ids": [
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000023",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000024",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000025",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000026"
    ]
  },
  {
    "topic": "复用技术",
    "summary": "复用概念，频分复用（FDM）、时分复用（TDM）及其同步时分复用示例（E1帧），以及同步时分复用的不足。",
    "difficulty": "medium",
    "estimated_minutes": 20,
    "related_material_ids": [
      "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
    ],
    "citation_chunk_ids": [
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000028",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000029",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000030",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000031",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000032"
    ]
  },
  {
    "topic": "物理层互连设备",
    "summary": "物理层互连设备包括中继器（Repeater）和集线器（HUB）。中继器连接两个网段并再生信号；HUB是多端口中继器，组成广播型LAN。",
    "difficulty": "easy",
    "estimated_minutes": 15,
    "related_material_ids": [
      "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
    ],
    "citation_chunk_ids": [
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000034",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000035",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000036",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000037",
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000038"
    ]
  },
  {
    "topic": "物理层的安全隐患",
    "summary": "物理层的安全隐患包括数据截获（从中继器、网卡、交换机、电磁脉冲等）。",
    "difficulty": "easy",
    "estimated_minutes": 10,
    "related_material_ids": [
      "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
    ],
    "citation_chunk_ids": [
      "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000040"
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
        "access_token": "<redacted>",
        "token_type": "bearer",
        "expires_at": "2026-07-12T17:06:55.787617Z",
        "user": {
          "id": "usr_1b1b3c4390164fd0949a0199e734a3f0",
          "username": "net_chap7_real_model",
          "nickname": null,
          "avatar_url": null,
          "status": "active",
          "created_at": "2026-07-11T17:06:55"
        }
      },
      "meta": {
        "request_id": "req_db1a0bcc1eb9428b995429231c2ea56e",
        "server_time": "2026-07-11T17:06:55.787617+00:00",
        "api_version": "v1"
      }
    }
  },
  "courses.create": {
    "status_code": 200,
    "body": {
      "data": {
        "id": "crs_a92069bde89b449e80c14bc241a2b59a",
        "user_id": "usr_1b1b3c4390164fd0949a0199e734a3f0",
        "name": "计算机网络",
        "description": null,
        "teacher": null,
        "term": null,
        "status": "active",
        "created_at": "2026-07-11T17:06:55",
        "updated_at": "2026-07-11T17:06:55",
        "deleted_at": null
      },
      "meta": {
        "request_id": "req_d64e2d040eab457e91b136cb647ce5c6",
        "server_time": "2026-07-11T17:06:55.815841+00:00",
        "api_version": "v1"
      }
    }
  },
  "materials.upload": {
    "status_code": 200,
    "body": {
      "data": {
        "id": "mat_42bc4a052a8647dd9d9c26d3cf9bdb26",
        "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
        "user_id": "usr_1b1b3c4390164fd0949a0199e734a3f0",
        "folder_id": null,
        "name": "Chap7 物理层.pdf",
        "material_type": "pdf",
        "source_type": "file",
        "file_url": "usr_1b1b3c4390164fd0949a0199e734a3f0/crs_a92069bde89b449e80c14bc241a2b59a/mat_42bc4a052a8647dd9d9c26d3cf9bdb26/source.pdf",
        "source_url": null,
        "file_size": 3635007,
        "mime_type": "application/pdf",
        "parse_status": "uploaded",
        "parse_error": null,
        "page_count": null,
        "created_at": "2026-07-11T17:06:55",
        "updated_at": "2026-07-11T17:06:55",
        "deleted_at": null
      },
      "meta": {
        "request_id": "req_06c72d2d862d4349ba458c9208a2063e",
        "server_time": "2026-07-11T17:06:55.885075+00:00",
        "api_version": "v1"
      }
    }
  },
  "materials.parse_retry": {
    "status_code": 200,
    "body": {
      "data": {
        "id": "mat_42bc4a052a8647dd9d9c26d3cf9bdb26",
        "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
        "user_id": "usr_1b1b3c4390164fd0949a0199e734a3f0",
        "folder_id": null,
        "name": "Chap7 物理层.pdf",
        "material_type": "pdf",
        "source_type": "file",
        "file_url": "usr_1b1b3c4390164fd0949a0199e734a3f0/crs_a92069bde89b449e80c14bc241a2b59a/mat_42bc4a052a8647dd9d9c26d3cf9bdb26/source.pdf",
        "source_url": null,
        "file_size": 3635007,
        "mime_type": "application/pdf",
        "parse_status": "parsed",
        "parse_error": null,
        "page_count": null,
        "created_at": "2026-07-11T17:06:55",
        "updated_at": "2026-07-11T17:09:28.985990",
        "deleted_at": null
      },
      "meta": {
        "request_id": "req_010a83abdaf846e38e60a7454ff45108",
        "server_time": "2026-07-11T17:09:28.988503+00:00",
        "api_version": "v1"
      }
    }
  },
  "study_plan_config_parse": {
    "status_code": 200,
    "body": {
      "data": {
        "goal_text": "我要两天学完计网这门课的第七章节",
        "start_date": "2026-07-12",
        "end_date": null,
        "daily_available_minutes": null,
        "preference": null,
        "material_scope": {
          "include_all_parsed_materials": true,
          "material_ids": []
        },
        "unresolved_fields": [
          "end_date",
          "daily_available_minutes",
          "preference"
        ]
      },
      "meta": {
        "request_id": "req_d5f8add0b6d742e9b8504f01076cb71e",
        "server_time": "2026-07-11T17:09:30.421758+00:00",
        "api_version": "v1"
      }
    }
  },
  "study_plans.preview": {
    "status_code": 200,
    "body": {
      "data": {
        "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
        "title": "计算机网路第七章物理层学习计划",
        "goal_text": "我要两天学完计网这门课的第七章节",
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
            "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
          ],
          "processed_material_ids": [
            "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
          ],
          "batch_count": 1
        },
        "tasks": [
          {
            "title": "第一天：物理层基础与数据通信",
            "task_date": "2026-07-12",
            "sort_order": 1,
            "subtasks": [
              {
                "title": "物理层概述与功能",
                "subtask_type": "learn",
                "description": "物理层是网络体系结构的最底层，负责将二进制数据编码成信号并通过传输介质发送，以及接收信号并转换为二进制数据。其功能包括定义机械、电气、功能和规程特性。",
                "related_material_ids": [
                  "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
                ],
                "estimated_minutes": 20,
                "citation_chunk_ids": [
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000003",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000004"
                ],
                "sort_order": 1
              },
              {
                "title": "数据通信基础知识",
                "subtask_type": "learn",
                "description": "包括信息、数据、信号、码元的概念，模拟与数字信号，信道分类，模拟通信与数字通信的区别，数据率与带宽，以及信道容量公式（奈奎斯特定理和香农定理）。",
                "related_material_ids": [
                  "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
                ],
                "estimated_minutes": 30,
                "citation_chunk_ids": [
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000007",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000008",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000009",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000010",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000011",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000012",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000013"
                ],
                "sort_order": 2
              },
              {
                "title": "传输介质",
                "subtask_type": "learn",
                "description": "传输介质包括有线介质（双绞线、同轴电缆、光纤）和无线介质（无线电、微波、卫星）。掌握它们的特点和应用场合。",
                "related_material_ids": [
                  "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
                ],
                "estimated_minutes": 20,
                "citation_chunk_ids": [
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000015",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000016",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000017",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000018",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000019",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000020",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000021"
                ],
                "sort_order": 3
              },
              {
                "title": "复习第一天内容",
                "subtask_type": "review",
                "description": "复习物理层概述、数据通信基础知识和传输介质，巩固理解。",
                "related_material_ids": [
                  "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
                ],
                "estimated_minutes": 30,
                "citation_chunk_ids": [],
                "sort_order": 4
              }
            ]
          },
          {
            "title": "第二天：调制编码、复用与设备",
            "task_date": "2026-07-13",
            "sort_order": 2,
            "subtasks": [
              {
                "title": "调制技术和编码技术",
                "subtask_type": "learn",
                "description": "模拟信号的特征（振幅、频率、相位），调制方法（如QAM），数字数据编码（NRZ-L、NRZI、曼彻斯特、差分曼彻斯特），以及脉冲编码调制PCM。",
                "related_material_ids": [
                  "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
                ],
                "estimated_minutes": 30,
                "citation_chunk_ids": [
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000023",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000024",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000025",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000026"
                ],
                "sort_order": 1
              },
              {
                "title": "复用技术",
                "subtask_type": "learn",
                "description": "复用概念，频分复用（FDM）、时分复用（TDM）及其同步时分复用示例（E1帧），以及同步时分复用的不足。",
                "related_material_ids": [
                  "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
                ],
                "estimated_minutes": 20,
                "citation_chunk_ids": [
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000028",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000029",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000030",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000031",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000032"
                ],
                "sort_order": 2
              },
              {
                "title": "物理层互连设备",
                "subtask_type": "learn",
                "description": "物理层互连设备包括中继器（Repeater）和集线器（HUB）。中继器连接两个网段并再生信号；HUB是多端口中继器，组成广播型LAN。",
                "related_material_ids": [
                  "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
                ],
                "estimated_minutes": 15,
                "citation_chunk_ids": [
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000034",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000035",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000036",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000037",
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000038"
                ],
                "sort_order": 3
              },
              {
                "title": "物理层的安全隐患",
                "subtask_type": "learn",
                "description": "物理层的安全隐患包括数据截获（从中继器、网卡、交换机、电磁脉冲等）。",
                "related_material_ids": [
                  "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
                ],
                "estimated_minutes": 10,
                "citation_chunk_ids": [
                  "chk_42bc4a052a8647dd9d9c26d3cf9bdb26_000040"
                ],
                "sort_order": 4
              },
              {
                "title": "综合复习与自测",
                "subtask_type": "quiz",
                "description": "复习调制编码、复用、设备和安全隐患，完成练习题或自测巩固知识。",
                "related_material_ids": [
                  "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
                ],
                "estimated_minutes": 45,
                "citation_chunk_ids": [],
                "sort_order": 5
              }
            ]
          }
        ]
      },
      "meta": {
        "request_id": "req_a7339dc58e864fe5a89d1e98609e523e",
        "server_time": "2026-07-11T17:10:00.653200+00:00",
        "api_version": "v1"
      }
    }
  },
  "study_plans.save": {
    "status_code": 200,
    "body": {
      "data": {
        "plan": {
          "id": "sp_7364bb437ce4435f9d597019d780974e",
          "user_id": "usr_1b1b3c4390164fd0949a0199e734a3f0",
          "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
          "title": "计算机网路第七章物理层学习计划",
          "goal_text": "我要两天学完计网这门课的第七章节",
          "parsed_config_json": {
            "material_scope": {
              "include_all_parsed_materials": true,
              "material_ids": []
            },
            "daily_available_minutes": 180,
            "preference": "balanced",
            "tasks_source": "confirmed",
            "idempotency": {
              "key_hash": "5f748353148dbdc3781784114a295fa2eedf451eda570b95b5f979ef4b9223ad",
              "request_hash": "485543baab7a78d1d9862a909b8822b9521a58244f2c04720ef0e8a0cfc704a5"
            }
          },
          "start_date": "2026-07-12",
          "end_date": "2026-07-13",
          "daily_available_minutes": 180,
          "status": "active",
          "created_at": "2026-07-11T17:10:00",
          "updated_at": "2026-07-11T17:10:00",
          "deleted_at": null
        },
        "tasks": [
          {
            "id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "第一天：物理层基础与数据通信",
            "task_date": "2026-07-12",
            "status": "not_started",
            "sort_order": 1,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "第二天：调制编码、复用与设备",
            "task_date": "2026-07-13",
            "status": "not_started",
            "sort_order": 2,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          }
        ],
        "subtasks": [
          {
            "id": "sub_e8f873ade0aa458785c5496c9c5703d2",
            "task_id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "物理层概述与功能",
            "subtask_type": "learn",
            "description": "物理层是网络体系结构的最底层，负责将二进制数据编码成信号并通过传输介质发送，以及接收信号并转换为二进制数据。其功能包括定义机械、电气、功能和规程特性。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 1,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_223d90fff8044aa38081ad85e9a8b1fa",
            "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "调制技术和编码技术",
            "subtask_type": "learn",
            "description": "模拟信号的特征（振幅、频率、相位），调制方法（如QAM），数字数据编码（NRZ-L、NRZI、曼彻斯特、差分曼彻斯特），以及脉冲编码调制PCM。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 1,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_e8501fa73d9242c993ac4206bc0633fd",
            "task_id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "数据通信基础知识",
            "subtask_type": "learn",
            "description": "包括信息、数据、信号、码元的概念，模拟与数字信号，信道分类，模拟通信与数字通信的区别，数据率与带宽，以及信道容量公式（奈奎斯特定理和香农定理）。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 2,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_8bb00aadb36641389359cc658776436d",
            "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "复用技术",
            "subtask_type": "learn",
            "description": "复用概念，频分复用（FDM）、时分复用（TDM）及其同步时分复用示例（E1帧），以及同步时分复用的不足。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 2,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_c8f2ed798f4148488243b4f0aef9b7b9",
            "task_id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "传输介质",
            "subtask_type": "learn",
            "description": "传输介质包括有线介质（双绞线、同轴电缆、光纤）和无线介质（无线电、微波、卫星）。掌握它们的特点和应用场合。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 3,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_f429bb0856544d9fa16f8e76d67cd585",
            "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "物理层互连设备",
            "subtask_type": "learn",
            "description": "物理层互连设备包括中继器（Repeater）和集线器（HUB）。中继器连接两个网段并再生信号；HUB是多端口中继器，组成广播型LAN。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 3,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_dc80585fcab04295b0ea2ed2a2b2436b",
            "task_id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "复习第一天内容",
            "subtask_type": "review",
            "description": "复习物理层概述、数据通信基础知识和传输介质，巩固理解。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 4,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_4539d6857ca4401ab985c98441745c2f",
            "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "物理层的安全隐患",
            "subtask_type": "learn",
            "description": "物理层的安全隐患包括数据截获（从中继器、网卡、交换机、电磁脉冲等）。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 4,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_eba50e8f220d42beaeb081854907712c",
            "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "综合复习与自测",
            "subtask_type": "quiz",
            "description": "复习调制编码、复用、设备和安全隐患，完成练习题或自测巩固知识。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 5,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          }
        ]
      },
      "meta": {
        "request_id": "req_38df659db82343f1a07f0210345ba698",
        "server_time": "2026-07-11T17:10:00.714885+00:00",
        "api_version": "v1"
      }
    }
  },
  "study_plans.list": {
    "status_code": 200,
    "body": {
      "data": [
        {
          "id": "sp_7364bb437ce4435f9d597019d780974e",
          "user_id": "usr_1b1b3c4390164fd0949a0199e734a3f0",
          "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
          "title": "计算机网路第七章物理层学习计划",
          "goal_text": "我要两天学完计网这门课的第七章节",
          "parsed_config_json": {
            "material_scope": {
              "include_all_parsed_materials": true,
              "material_ids": []
            },
            "daily_available_minutes": 180,
            "preference": "balanced",
            "tasks_source": "confirmed",
            "idempotency": {
              "key_hash": "5f748353148dbdc3781784114a295fa2eedf451eda570b95b5f979ef4b9223ad",
              "request_hash": "485543baab7a78d1d9862a909b8822b9521a58244f2c04720ef0e8a0cfc704a5"
            }
          },
          "start_date": "2026-07-12",
          "end_date": "2026-07-13",
          "daily_available_minutes": 180,
          "status": "active",
          "created_at": "2026-07-11T17:10:00",
          "updated_at": "2026-07-11T17:10:00",
          "deleted_at": null
        }
      ],
      "meta": {
        "request_id": "req_2eae8e4b6c304302ba4593e837812272",
        "server_time": "2026-07-11T17:10:00.737896+00:00",
        "api_version": "v1"
      }
    }
  },
  "study_plans.detail": {
    "status_code": 200,
    "body": {
      "data": {
        "plan": {
          "id": "sp_7364bb437ce4435f9d597019d780974e",
          "user_id": "usr_1b1b3c4390164fd0949a0199e734a3f0",
          "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
          "title": "计算机网路第七章物理层学习计划",
          "goal_text": "我要两天学完计网这门课的第七章节",
          "parsed_config_json": {
            "material_scope": {
              "include_all_parsed_materials": true,
              "material_ids": []
            },
            "daily_available_minutes": 180,
            "preference": "balanced",
            "tasks_source": "confirmed",
            "idempotency": {
              "key_hash": "5f748353148dbdc3781784114a295fa2eedf451eda570b95b5f979ef4b9223ad",
              "request_hash": "485543baab7a78d1d9862a909b8822b9521a58244f2c04720ef0e8a0cfc704a5"
            }
          },
          "start_date": "2026-07-12",
          "end_date": "2026-07-13",
          "daily_available_minutes": 180,
          "status": "active",
          "created_at": "2026-07-11T17:10:00",
          "updated_at": "2026-07-11T17:10:00",
          "deleted_at": null
        },
        "tasks": [
          {
            "id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "第一天：物理层基础与数据通信",
            "task_date": "2026-07-12",
            "status": "not_started",
            "sort_order": 1,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "第二天：调制编码、复用与设备",
            "task_date": "2026-07-13",
            "status": "not_started",
            "sort_order": 2,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          }
        ],
        "subtasks": [
          {
            "id": "sub_e8f873ade0aa458785c5496c9c5703d2",
            "task_id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "物理层概述与功能",
            "subtask_type": "learn",
            "description": "物理层是网络体系结构的最底层，负责将二进制数据编码成信号并通过传输介质发送，以及接收信号并转换为二进制数据。其功能包括定义机械、电气、功能和规程特性。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 1,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_223d90fff8044aa38081ad85e9a8b1fa",
            "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "调制技术和编码技术",
            "subtask_type": "learn",
            "description": "模拟信号的特征（振幅、频率、相位），调制方法（如QAM），数字数据编码（NRZ-L、NRZI、曼彻斯特、差分曼彻斯特），以及脉冲编码调制PCM。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 1,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_e8501fa73d9242c993ac4206bc0633fd",
            "task_id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "数据通信基础知识",
            "subtask_type": "learn",
            "description": "包括信息、数据、信号、码元的概念，模拟与数字信号，信道分类，模拟通信与数字通信的区别，数据率与带宽，以及信道容量公式（奈奎斯特定理和香农定理）。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 2,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_8bb00aadb36641389359cc658776436d",
            "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "复用技术",
            "subtask_type": "learn",
            "description": "复用概念，频分复用（FDM）、时分复用（TDM）及其同步时分复用示例（E1帧），以及同步时分复用的不足。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 2,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_c8f2ed798f4148488243b4f0aef9b7b9",
            "task_id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "传输介质",
            "subtask_type": "learn",
            "description": "传输介质包括有线介质（双绞线、同轴电缆、光纤）和无线介质（无线电、微波、卫星）。掌握它们的特点和应用场合。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 3,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_f429bb0856544d9fa16f8e76d67cd585",
            "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "物理层互连设备",
            "subtask_type": "learn",
            "description": "物理层互连设备包括中继器（Repeater）和集线器（HUB）。中继器连接两个网段并再生信号；HUB是多端口中继器，组成广播型LAN。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 3,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_dc80585fcab04295b0ea2ed2a2b2436b",
            "task_id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "复习第一天内容",
            "subtask_type": "review",
            "description": "复习物理层概述、数据通信基础知识和传输介质，巩固理解。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 4,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_4539d6857ca4401ab985c98441745c2f",
            "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "物理层的安全隐患",
            "subtask_type": "learn",
            "description": "物理层的安全隐患包括数据截获（从中继器、网卡、交换机、电磁脉冲等）。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 4,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          },
          {
            "id": "sub_eba50e8f220d42beaeb081854907712c",
            "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
            "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
            "course_id": "crs_a92069bde89b449e80c14bc241a2b59a",
            "title": "综合复习与自测",
            "subtask_type": "quiz",
            "description": "复习调制编码、复用、设备和安全隐患，完成练习题或自测巩固知识。",
            "related_material_ids_json": [
              "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
            ],
            "status": "not_started",
            "completed_at": null,
            "sort_order": 5,
            "created_at": "2026-07-11T17:10:00",
            "updated_at": "2026-07-11T17:10:00"
          }
        ]
      },
      "meta": {
        "request_id": "req_ea23137ac73742769ed8fca64c717ac1",
        "server_time": "2026-07-11T17:10:00.749877+00:00",
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
      "id": "sp_7364bb437ce4435f9d597019d780974e",
      "title": "计算机网路第七章物理层学习计划",
      "goal_text": "我要两天学完计网这门课的第七章节",
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
          "key_hash": "5f748353148dbdc3781784114a295fa2eedf451eda570b95b5f979ef4b9223ad",
          "request_hash": "485543baab7a78d1d9862a909b8822b9521a58244f2c04720ef0e8a0cfc704a5"
        }
      }
    }
  ],
  "study_tasks": [
    {
      "id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
      "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
      "title": "第一天：物理层基础与数据通信",
      "task_date": "2026-07-12",
      "status": "not_started",
      "sort_order": 1
    },
    {
      "id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
      "plan_id": "sp_7364bb437ce4435f9d597019d780974e",
      "title": "第二天：调制编码、复用与设备",
      "task_date": "2026-07-13",
      "status": "not_started",
      "sort_order": 2
    }
  ],
  "study_subtasks": [
    {
      "id": "sub_e8f873ade0aa458785c5496c9c5703d2",
      "task_id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
      "title": "物理层概述与功能",
      "subtask_type": "learn",
      "description": "物理层是网络体系结构的最底层，负责将二进制数据编码成信号并通过传输介质发送，以及接收信号并转换为二进制数据。其功能包括定义机械、电气、功能和规程特性。",
      "related_material_ids_json": [
        "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
      ],
      "status": "not_started",
      "sort_order": 1
    },
    {
      "id": "sub_223d90fff8044aa38081ad85e9a8b1fa",
      "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
      "title": "调制技术和编码技术",
      "subtask_type": "learn",
      "description": "模拟信号的特征（振幅、频率、相位），调制方法（如QAM），数字数据编码（NRZ-L、NRZI、曼彻斯特、差分曼彻斯特），以及脉冲编码调制PCM。",
      "related_material_ids_json": [
        "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
      ],
      "status": "not_started",
      "sort_order": 1
    },
    {
      "id": "sub_e8501fa73d9242c993ac4206bc0633fd",
      "task_id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
      "title": "数据通信基础知识",
      "subtask_type": "learn",
      "description": "包括信息、数据、信号、码元的概念，模拟与数字信号，信道分类，模拟通信与数字通信的区别，数据率与带宽，以及信道容量公式（奈奎斯特定理和香农定理）。",
      "related_material_ids_json": [
        "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
      ],
      "status": "not_started",
      "sort_order": 2
    },
    {
      "id": "sub_8bb00aadb36641389359cc658776436d",
      "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
      "title": "复用技术",
      "subtask_type": "learn",
      "description": "复用概念，频分复用（FDM）、时分复用（TDM）及其同步时分复用示例（E1帧），以及同步时分复用的不足。",
      "related_material_ids_json": [
        "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
      ],
      "status": "not_started",
      "sort_order": 2
    },
    {
      "id": "sub_c8f2ed798f4148488243b4f0aef9b7b9",
      "task_id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
      "title": "传输介质",
      "subtask_type": "learn",
      "description": "传输介质包括有线介质（双绞线、同轴电缆、光纤）和无线介质（无线电、微波、卫星）。掌握它们的特点和应用场合。",
      "related_material_ids_json": [
        "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
      ],
      "status": "not_started",
      "sort_order": 3
    },
    {
      "id": "sub_f429bb0856544d9fa16f8e76d67cd585",
      "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
      "title": "物理层互连设备",
      "subtask_type": "learn",
      "description": "物理层互连设备包括中继器（Repeater）和集线器（HUB）。中继器连接两个网段并再生信号；HUB是多端口中继器，组成广播型LAN。",
      "related_material_ids_json": [
        "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
      ],
      "status": "not_started",
      "sort_order": 3
    },
    {
      "id": "sub_dc80585fcab04295b0ea2ed2a2b2436b",
      "task_id": "tsk_2c8df68f0c9d4c149dccdcbe697ee160",
      "title": "复习第一天内容",
      "subtask_type": "review",
      "description": "复习物理层概述、数据通信基础知识和传输介质，巩固理解。",
      "related_material_ids_json": [
        "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
      ],
      "status": "not_started",
      "sort_order": 4
    },
    {
      "id": "sub_4539d6857ca4401ab985c98441745c2f",
      "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
      "title": "物理层的安全隐患",
      "subtask_type": "learn",
      "description": "物理层的安全隐患包括数据截获（从中继器、网卡、交换机、电磁脉冲等）。",
      "related_material_ids_json": [
        "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
      ],
      "status": "not_started",
      "sort_order": 4
    },
    {
      "id": "sub_eba50e8f220d42beaeb081854907712c",
      "task_id": "tsk_18408f9ef2d841fb965ab9a49d234fa9",
      "title": "综合复习与自测",
      "subtask_type": "quiz",
      "description": "复习调制编码、复用、设备和安全隐患，完成练习题或自测巩固知识。",
      "related_material_ids_json": [
        "mat_42bc4a052a8647dd9d9c26d3cf9bdb26"
      ],
      "status": "not_started",
      "sort_order": 5
    }
  ],
  "checkin_records": [
    {
      "id": "chkrec_5b4d52c0040e4ff486facebb6be2f242",
      "checkin_date": "2026-07-12",
      "total_subtask_count": 4,
      "completed_subtask_count": 0,
      "completion_ratio": "0.0000",
      "color_level": 1
    },
    {
      "id": "chkrec_75fb3e400bdb433da4b7d6185ce0af5f",
      "checkin_date": "2026-07-13",
      "total_subtask_count": 5,
      "completed_subtask_count": 0,
      "completion_ratio": "0.0000",
      "color_level": 1
    }
  ]
}
```

