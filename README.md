# 八字排盘引擎 (Bazi Engine)

独立开发的八字命理分析引擎。规则引擎负责精确计算与信号检测，LLM 推理层负责边界年份的多弱信号综合判断。

> 本引擎为独立原创开发，仅在早期灵感上参考了开源社区工作。

## 功能

### 精确排盘
- **四柱计算** — 年/月/日/时柱，ephem 天文库节气精度 ±1 秒
- **真太阳时口径** — 离线覆盖全国市级和区县级行政区划；有坐标时按经度与均时差校正，地点未知或暂无坐标时严格保留用户输入时间
- **藏干十神** — 地支藏干（本气/中气/余气），天干十神定位
- **格局判定** — 月令透干优先 + 建禄/羊刃特殊处理
- **神煞检测** — 天乙贵人/红鸾/天喜/桃花/驿马/文昌/羊刃/灾煞/丧门/吊客
- **纳音命宫** — 纳音五行 + 命宫/身宫/胎元
- **十二长生** — 阴阳分轨，10 天干独立映射表

### 流年事件扫描（7 类）
| 类别 | 检测方式 | 证据状态 |
|------|---------|----------|
| 婚嫁/桃花 | 关系与神煞的文化提示 | 非预测准确率 |
| 事业 | 十神与关系的工程信号 | 非预测准确率 |
| 财运 | 十神与原局财库关系 | 非预测准确率 |
| 健康 | 生活节律与安全提醒 | 不构成医疗判断 |
| 人际 | 十神与关系信号 | 非预测准确率 |
| 搬迁 | 驿马与冲合关系 | 非预测准确率 |
| 状态 | 十神与日柱关系 | 非预测准确率 |

### 规则与边界层

规则分为古籍摘要、古籍推导、现代流派、工程启发式和案例观察；案例观察不直接升级为通用规则。

| 检查点 | 描述 |
|--------|------|
| 调候观察 | 寒暖燥湿的独立参考，不单独判定废局 |
| 假生陷阱 | 水冷木冻/燥土脆金/湿木不生火 |
| 十二长生分轨 | 阳生阴死，接入强弱计算 |
| 墓库关系 | 仅记录辰戌、丑未实际六冲，不作倍增或疾病/暴富推断 |
| 同柱隔离带 | 截脚/盖头 → 流年内部能量消耗 |
| 从格限制 | 有日主或印星明根、暗根时不自动判从 |
| 贪生忘克 | 天干相邻连环相生化解克制 |

### 大运调制层（v0.8.0）
- **DayunModulator** — 每步大运与原局合冲刑害 → 喜忌基线偏移
- **岁运交战** — 天战/地战/刑害分层拦截，地战权重 1.5-2x
- **主题加权** — 大运十神主题与流年类别共振加权

### LLM 推理层（v0.9.0）
- **Hybrid 模式** — 规则引擎主跑，LLM 介入目标类别尚未被规则强信号完整覆盖的边界年份
- **流年近失特征** — 十神/神煞/冲合/空亡等规则引擎内算但未触发的特征传给 LLM
- **DeepSeek 集成** — 支持 `deepseek-chat`/`deepseek-v4-pro`/`deepseek-v4-flash`；年度审阅可通过 `BAZI_LLM_REVIEW_MODEL` 独立选择低延迟模型
- **开关控制** — `BAZI_LLM_REVIEW=1` 启用，默认关闭

## 安装

```bash
git clone https://github.com/jiwenxu025-boop/bazi-engine.git
cd bazi-engine
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 使用

### CLI

```bash
cd scripts
PYTHONIOENCODING=utf-8 python -m bazi_engine.cli \
  --name "姓名" --gender 男 \
  --year 1990 --month 6 --day 15 --hour 8 \
  --liunian 2023-2030
```

### API 服务

```bash
cd scripts
python -m uvicorn bazi_engine.api:app --host 0.0.0.0 --port 8000
```

浏览器打开 `http://localhost:8000` 使用前端界面。

出生城市或区县由全国离线清单搜索选择，可按名称、完整行政路径、拼音或行政代码检索；未选地点默认“未知”。高级设置可填写手动经度和时区。时间口径、校正分钟数、UTC 出生瞬间和最终排盘时间会写入报告元数据，详见 [时间口径](docs/time-basis.md)。

### 测试

```bash
python -m pip install -r requirements-dev.txt
cd scripts
python -m pytest tests/ -q

# 校准测试
python tests/calibration_marriage.py
python tests/calibration_career.py
python tests/calibration_wealth.py
python tests/calibration_others.py
```

## 引擎架构

```
bazi-engine/
├── SKILL.md                        # Claude Code Skill 入口
├── README.md
├── Procfile                        # 部署配置
├── requirements.txt
├── scripts/
│   ├── bazi_engine/                # Python 引擎包
│   │   ├── enums.py                #   天干/地支/五行/十神枚举
│   │   ├── _constants.py           #   全部查表数据（合冲刑害/神煞/藏干/十二长生）
│   │   ├── _imagery.py             #   意象文本
│   │   ├── solar_terms.py          #   ephem 精确节气计算
│   │   ├── pillars.py              #   年/月/日/时柱计算
│   │   ├── ten_gods.py             #   十神分配
│   │   ├── pattern.py              #   格局判定（月令透干优先）
│   │   ├── yongshen.py             #   用神推荐（强弱+调候+从格+假生+长生修正）
│   │   ├── tiaohou.py              #   调候独立分析 + 假生陷阱检测
│   │   ├── interactions.py         #   合冲刑害 + 墓库关系记录 + 贪生忘克
│   │   ├── spirits.py              #   神煞检测
│   │   ├── dayun.py                #   大运计算 + DayunModulator
│   │   ├── liunian.py              #   7 类流年事件扫描 + 岁运交战
│   │   ├── llm_review.py           #   LLM 推理层（Hybrid 模式）
│   │   ├── changsheng_analysis.py  #   十二长生参断
│   │   ├── nayin_chain.py          #   纳音生克链
│   │   ├── palace_star.py          #   宫位叠象
│   │   ├── body_use.py             #   宾主体用 + 墓库应期
│   │   ├── void_god.py             #   藏干虚神
│   │   ├── chart.py                #   BaziChart + build_chart() 工厂
│   │   ├── api.py                  #   FastAPI 服务
│   │   ├── chat.py                 #   DeepSeek AI 追问（流式 SSE）
│   │   └── cli.py                  #   命令行入口
│   ├── data/
│   │   └── calibration_store.json  #   校准数据库
│   └── tests/
│       ├── test_engine.py          #   三案例排盘验证
│       ├── test_calibration.py     #   校准数据库验证
│       ├── test_solar_terms.py     #   节气精度测试
│       ├── calibration_marriage.py #   婚嫁/桃花校准（22 例）
│       ├── calibration_career.py   #   事业校准（18 例）
│       ├── calibration_wealth.py   #   财运校准（24 例）
│       └── calibration_others.py   #   人际/状态/搬迁/健康校准
├── frontend/
│   ├── index.html                  #   SPA 主页面
│   ├── app.js                      #   前端逻辑
│   ├── chat.css                    #   AI 聊天面板样式
│   ├── privacy.html                #   隐私政策
│   └── terms.html                  #   服务协议
└── references/                     #   参考文档
    ├── wuxing-tables.md
    ├── shichen-table.md
    ├── dayun-rules.md
    ├── calibration-notes.md
    ├── classical-texts.md
    └── personality-rules.md
```

## 参考典籍

| 典籍 | 用途 |
|------|------|
| 《穷通宝鉴》 | 调候优先、十天干喜忌 |
| 《三命通会》 | 格局神煞、大运流年 |
| 《滴天髓》 | 五行旺衰、干支体用 |
| 《渊海子平》 | 十神六亲、用神格局 |
| 《子平真诠》 | 格局顺逆、善神凶神 |
| 陆致极《八字命理学进阶教程》 | 调候为先、格局用神体系 |
| 梁湘润《八字实务》 | 干支作用、墓库应期 |
| 段建业《盲派命理》 | 宫位星位、冲合应期 |

## 公开部署

### Railway

1. Fork 或 Clone 本仓库到你的 GitHub
2. 在 [Railway](https://railway.app) 新建项目 → Deploy from GitHub → 选择本仓库
3. 添加环境变量：
   ```
   BAZI_PUBLIC=true
   DEEPSEEK_API_KEY=          # 可选，启用 AI 追问，不要提交到仓库
   DEEPSEEK_MODEL=deepseek-v4-flash
   BAZI_LLM_CONTEXT_LIMIT=1000000  # 上下文上限（含预留输出），实际请求不会填充到该长度
   BAZI_LLM_REVIEW=1          # 可选，启用 LLM 推理层
   ```
4. 部署完成后获得公网 URL

### 本地前端

浏览器打开 `frontend/index.html`，API 地址填写公网 URL 即可远程排盘。

### 生产运维

生产环境变量请从 `.env.example` 创建，并保存在仓库外或受权限保护的 `.env` 中。部署、回滚、备份和公网 HTTP 风险说明见 [docs/operations.md](docs/operations.md)。

## 免责声明

本引擎仅供传统文化学习与娱乐参考，分析结果不构成任何决策依据。命理学属于传统文化范畴，请理性看待。


---
