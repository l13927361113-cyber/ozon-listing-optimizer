# OZON商品文案 / OZON Listing 优化

独立于北极星进销存的 OZON Listing 工作台。

## 当前版本 V1.5.7
- 新商品：整机 / 零件 / 其他商品
- 旧商品 Listing 优化
- 零件号智能查询与文案修正
- 零件号识别支持字母开头、纯数字、连字符及混合编号；支持手动确认/修正
- 得伟/史丹利：以中国市场型号及Type为首要核验入口，交叉比对俄罗斯/欧美市场型号、地区共用零件及不同代际替代关系
- ChatGPT Plus 手动联网核验；Render 不执行外部检索、不需要额外 API
- Neon PostgreSQL / 本地 SQLite

## 部署
GitHub → Render → Neon。
不要把 OPENAI_API_KEY 提交到 GitHub。


## V1.5.8 修复
- 文案库支持直接修改并保存零件号（不修改文案正文），包括 N 前缀、字母数字混合编号和多编号。
- 生成/修订 ChatGPT 指令加强 DeWALT、Stanley 中国 A9 优先、EU/QW/RU 地区 Type 核验、跨地区零件号替代调查和文案范围约束。
- 如修改实际零件号，必须使用全篇修订模式重新核验标题、描述、标签和包装清单；不能仅改 Part3/4。
- 保留现有 Neon 数据和记录编号，无数据库迁移；ZIP 不会自动部署到 Render。
