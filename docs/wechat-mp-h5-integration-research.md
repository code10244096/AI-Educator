# H5 网页应用接入微信公众号调研报告（面向中小学教师的 AI 教育产品·体验版）

> 调研时间：2026 年 10 月；规则以微信公众平台、微信开放文档及教育部现行文件为准，动态调整处已标注「需以官方最新公告为准」。

## 一、公众号类型怎么选

| 类型 | 主体 | 菜单挂外链 | 网页授权（拿 openid） | JS-SDK | 备注 |
|---|---|---|---|---|---|
| 服务号（已认证） | 企业/组织，不支持个人 | ✅ | ✅（仅认证服务号有此接口权限） | ✅ 完整 | 每月群发 4 次，支持微信支付/模板消息，**接入 H5 的正解** |
| 服务号（未认证） | 企业/组织 | ✅（官方社区确认：非个人服务号不认证也可菜单跳外链） | ❌ | ❌ | 可做最简引流 |
| 订阅号/公众号（已认证，组织类） | 企业/组织/个人（个人不可认证） | ✅ | ❌ | 部分 | 每天群发 1 次，适合内容运营 |
| 订阅号（未认证/个人） | 个人/组织 | ❌（菜单只能跳站内素材/历史消息） | ❌ | ❌ | 只能靠「阅读原文」、自动回复文字链接、二维码 |
| 企业微信 | 企业 | — | OAuth 拿的是 UserID 而非 openid | ✅ | 适合面向学校组织做 B 端客户联系，不替代公众号 C 端入口 |

注意：2025 年起公众平台注册页已将「订阅号」合并显示为「公众号」，能力差异不变；账号类型注册后不可直接互转（只能走账号迁移），**选型需一次到位**。

## 二、注册与微信认证

- 注册免费（mp.weixin.qq.com），邮箱激活 + 主体信息 + 管理员微信扫码即可，当天完成。
- 微信认证 **300 元/次，有效期一年，到期年审同为 300 元/年**，无论通过与否不退款。
- 材料：营业执照（清晰扫描件）、认证公函（盖章）、运营者/法人身份证；企业需对公账户小额打款验证，个体工商户可用法人银行卡/扫脸替代。
- 审核约 1–3 个工作日（部分渠道称 3–5 个，需以官方最新公告为准）。
- 个人主体订阅号不能认证，也注册不了服务号——教育产品面向教师群体运营，**必须用企业/个体户主体**。

## 三、网页接入技术要求

1. **ICP 备案（硬门槛）**：JS 接口安全域名、网页授权域名均要求域名已完成工信部 ICP 备案，新备案域名需约 24 小时后才能配置；未备案域名在微信内会被拦截（「已停止访问该网页」/「无法确认网页安全性」）。
2. **HTTPS（硬门槛）**：所有配置域名仅支持 https，不支持 IP；SSL 证书须为受信任 CA 签发（免费证书如 Let's Encrypt/云厂商免费证书可用）。
3. **三类域名配置**（公众平台 → 设置与开发 → 公众号设置 → 功能设置，需管理员扫码）：
   - JS 接口安全域名：调用 JS-SDK（分享、拍照、定位等），每号最多 5 个、每月最多改 5 次，需在域名根目录放置校验文件；
   - 网页授权域名：OAuth2.0 回调域，redirect_uri 必须与配置域名完全一致；
   - 业务域名：菜单/消息跳转场景。
4. **网页授权（OAuth2.0）拿 openid 流程**：引导用户访问 `https://open.weixin.qq.com/connect/oauth2/authorize?appid=APPID&redirect_uri=REDIRECT_URI&response_type=code&scope=snsapi_base&state=STATE#wechat_redirect` → 回调带回一次性 code → **后端**用 appid+secret 换网页 access_token 和 openid（snsapi_base 静默只拿 openid；snsapi_userinfo 弹窗可拿昵称头像）。secret 严禁出现在前端。**此能力仅已认证服务号具备。**

## 四、教育类特殊资质

- **教育移动应用备案（提供者备案）**：教育部《教育移动互联网应用程序备案管理办法》明确备案范围含「教育 APP、微信公众号、小程序、H5」，凡以教职工/学生/家长为主要用户、服务学校教学管理的应用均属此列——本产品面向中小学教师，**基本确定落入范围**。前置条件：ICP 备案 + 网络安全等级保护定级备案；在全国教育移动互联网应用程序备案管理平台（app.eduyun.cn）向注册地省级教育行政部门申报。学校侧还有「使用者备案」，未备案产品原则上不得进校（北京等地细则明确「非必要、不选用」）。
- **校外培训监管**：面向中小学生提供学科类线上培训才触发「双减」后的审批制监管（ICP 许可证、教师资格证公示等）；面向教师的工具类产品一般不触发，但体验版若含学生端需谨慎评估（需以官方最新公告为准）。
- **ICP 经营许可证**：体验版免费 → 只需 ICP 备案；后续若线上收费（会员订阅等经营性信息服务）→ 需办增值电信业务经营许可证（ICP 证）。
- 有渠道称 2025 年起 AI 教学工具需算法备案，权威来源不足，**需以官方最新公告为准**。

## 五、不认证的替代路径

不花 300 元也能起步：① 注册**企业主体未认证服务号**，菜单可直接挂 H5 外链（微信开放社区官方确认）；② 「阅读原文」、关键词/被关注自动回复中的 `<a>` 链接、图文内二维码，所有类型公众号可用。缺的是网页授权（拿不到 openid，无法做微信内免登）和 JS-SDK。小程序 vs 公众号 H5：小程序体验好、入口多、可订阅消息，但需类目资质审核、每次发版过审；H5 迭代自由、可复用到微信外渠道，但无留存入口。**常见做法是「公众号做触达 + H5 快速验证，验证后再补小程序」**。

## 六、时间线与成本估算

| 事项 | 周期 | 费用 |
|---|---|---|
| 公众号注册 | 当天 | 0 |
| 域名 + ICP 备案（若未完成） | 约 1–3 周（各地管局差异大） | 域名约数十元/年，备案免费 |
| 微信认证 | 1–3 个工作日 | 300 元/年 |
| 等保定级备案（教育备案前置） | 2–4 周起 | 自评低成本；如需三级测评则数万元 |
| 教育移动应用提供者备案 | 数周（省级核验） | 0 |
| 域名配置 + OAuth 联调 | 1–2 周 | 开发人力 |

最简可用路径（已有备案域名 + 企业主体）：**约 1 周、300 元/年**即可上线菜单挂 H5；完整合规路径（含等保 + 教育备案）：**约 1.5–3 个月**。

## 来源列表

1. [微信官方：域名管理（JS 接口安全域名/业务域名/网页授权域名，ICP 备案+HTTPS 要求）](kimi-cite://web?url=https%3A%2F%2Fdevelopers.weixin.qq.com%2Fdoc%2Foplatform%2Fdevelopers%2Fbasic_func%2Fdomain.html&text=%E5%9F%9F%E5%90%8D%E5%8F%AA%E6%94%AF%E6%8C%81%20https%20%E5%8D%8F%E8%AE%AE%EF%BC%8C%E4%B8%8D%E6%94%AF%E6%8C%81%20IP%20%E5%9C%B0%E5%9D%80%20%E5%9F%9F%E5%90%8D%E9%9C%80%E7%BB%8F%E8%BF%87%20ICP%20%E5%A4%87%E6%A1%88 "citation")
2. [微信开放社区：非个人服务号不认证菜单也可跳外链](kimi-cite://web?url=https%3A%2F%2Fdevelopers.weixin.qq.com%2Fcommunity%2Fdevelop%2Fdoc%2F0000a8c3e44ff86c72a3fb51d6bc00&text=%E9%9D%9E%E4%B8%AA%E4%BA%BA%E7%B1%BB%E5%9E%8B%E6%9C%8D%E5%8A%A1%E5%8F%B7%E6%97%A0%E8%AE%BA%E6%98%AF%E5%90%A6%E5%AE%8C%E6%88%90%E5%BE%AE%E4%BF%A1%E8%AE%A4%E8%AF%81%EF%BC%8C%E8%8F%9C%E5%8D%95%E5%8F%AF%E4%BB%A5%E8%B7%B3%E8%BD%AC%E5%A4%96%E9%93%BE "citation")
3. [微信开放社区：公众号年审流程与 300 元费用（引用 kf.qq.com 官方 FAQ）](kimi-cite://web?url=https%3A%2F%2Fdevelopers.weixin.qq.com%2Fcommunity%2Fminihome%2Fdoc%2F0006e0f126487087a6a3419da61c00&text=%E8%AE%A4%E8%AF%81%E8%B4%B9%E7%94%A8%E7%BB%9F%E4%B8%80%E4%B8%BA300%E5%85%83%2F%E6%AC%A1 "citation")
4. [腾讯云开发者社区：只有认证过的服务号才有网页授权权限](kimi-cite://web?url=https%3A%2F%2Fcloud.tencent.com%2Fdeveloper%2Farticle%2F2592140&text=%E5%8F%AA%E6%9C%89%E8%AE%A4%E8%AF%81%E8%BF%87%E7%9A%84%E6%9C%8D%E5%8A%A1%E5%8F%B7%E6%89%8D%E6%9C%89%E7%BD%91%E9%A1%B5%E6%8E%88%E6%9D%83%E6%9D%83%E9%99%90 "citation")
5. [教育部等六部门《关于规范校外线上培训的实施意见》（moe.gov.cn）](kimi-cite://web?url=http%3A%2F%2Fwww.moe.gov.cn%2Fsrcsite%2FA06%2Fs3325%2F201907%2Ft20190715_390502.html&text=%E6%A0%A1%E5%A4%96%E7%BA%BF%E4%B8%8A%E5%9F%B9%E8%AE%AD%E6%9C%BA%E6%9E%84%E5%A4%87%E6%A1%88%E6%9D%90%E6%96%99%E4%B8%BB%E8%A6%81%E5%8C%85%E6%8B%AC%EF%BC%9A%E5%9F%B9%E8%AE%AD%E6%9C%BA%E6%9E%84%E7%9A%84ICP "citation")
6. [广东省教育厅：教育移动应用备案实施细则（范围含公众号/小程序/H5）](kimi-cite://web?url=https%3A%2F%2Fedu.gd.gov.cn%2Fzwgknew%2Fgsgg%2Fcontent%2Fpost_3429197.html&text=%E5%8C%85%E6%8B%AC%E5%90%84%E7%B1%BB%E6%95%99%E8%82%B2APP%E3%80%81%E5%BE%AE%E4%BF%A1%E5%B9%B3%E5%8F%B0%E5%85%AC%E4%BC%97%E5%8F%B7%E3%80%81%E5%B0%8F%E7%A8%8B%E5%BA%8F%E3%80%81H5%E7%AD%89 "citation")
7. [北京市教委：教育 APP 备案实施细则（未备案不得选用）](kimi-cite://web?url=https%3A%2F%2Fwww.beijing.gov.cn%2Fzhengce%2Fzhengcefagui%2F202410%2Ft20241029_3930108.html&text=%E5%87%A1%E6%9C%AA%E9%80%9A%E8%BF%87%E6%95%99%E8%82%B2%E9%83%A8%E5%A4%87%E6%A1%88%E7%9A%84%EF%BC%8C%E4%B8%80%E5%BE%8B%E4%B8%8D%E5%BE%97%E9%80%89%E7%94%A8 "citation")
8. [教育移动应用备案平台帮助中心（app.eduyun.cn）](kimi-cite://web?url=https%3A%2F%2Fapp.eduyun.cn%2Fbmp-web%2Fmapp%2FhelpCenter%2F6&text=%E6%9C%AA%E5%A4%87%E6%A1%88%E7%9A%84%E6%95%99%E8%82%B2APP%E5%8E%9F%E5%88%99%E4%B8%8A%E4%B8%8D%E5%85%81%E8%AE%B8%E8%BF%9B%E6%A0%A1 "citation")
9. [汉坤律所：在线教育资质要求（经营性需 ICP 证，免费只需 ICP 备案）](kimi-cite://web?url=https%3A%2F%2Fwww.hanyilaw.com%2Fupload%2F202112%2F6be2559a-dcb5-4166-ae7c-967f70fc5fe6.pdf&text=%E5%85%B3%E9%94%AE%E5%9C%A8%E4%BA%8E%E5%9C%A8%E7%BA%BF%E6%95%99%E8%82%B2%E4%BC%81%E4%B8%9A%E6%98%AF%E5%90%A6%E5%B0%B1%E7%BA%BF%E4%B8%8A%E6%95%99%E8%82%B2%E5%86%85%E5%AE%B9%E6%88%96%E6%9C%8D%E5%8A%A1%E6%94%B6%E8%B4%B9 "citation")
10. [CSDN：微信内网页拦截与 ICP 备案/HTTPS 关系](kimi-cite://web?url=https%3A%2F%2Fblog.csdn.net%2Fweixin_29323365%2Farticle%2Fdetails%2F162186450&text=%E5%9F%9F%E5%90%8D%E6%B2%A1%E6%9C%89%E5%AE%8C%E6%88%90%E5%B7%A5%E4%BF%A1%E9%83%A8%E7%9A%84ICP%E5%A4%87%E6%A1%88%EF%BC%8C%E5%BE%AE%E4%BF%A1%E5%A4%A7%E6%A6%82%E7%8E%87%E4%BC%9A%E6%8B%A6%E6%88%AA "citation")
11. [搜狐 2026：订阅号/服务号定位差异](kimi-cite://web?url=https%3A%2F%2Fwww.sohu.com%2Fa%2F1047184034_120000988&text=%E6%9C%8D%E5%8A%A1%E5%8F%B7%EF%BC%9A%E4%BC%81%E4%B8%9A%E6%9C%8D%E5%8A%A1%E7%AA%97%E5%8F%A3%20%E4%B8%BB%E6%89%93%E7%BA%BF%E4%B8%8A%E4%B8%9A%E5%8A%A1%E9%97%AD%E7%8E%AF%EF%BC%8C%E6%8B%A5%E6%9C%89%E5%AE%8C%E6%95%B4%E9%AB%98%E7%BA%A7%E5%BC%80%E5%8F%91%E6%8E%A5%E5%8F%A3 "citation")
12. [人人都是产品经理：H5 与小程序取舍对比](kimi-cite://web?url=https%3A%2F%2Fwww.woshipm.com%2Fpd%2F1315132.html&text=%E5%B0%8F%E7%A8%8B%E5%BA%8F%E7%9A%84%E7%89%B9%E7%82%B9%EF%BC%8C%E5%B0%B1%E6%98%AF%E6%AF%8F%E6%AC%A1%E6%8F%90%E4%BA%A4%E7%89%88%E6%9C%AC%E9%83%BD%E8%A6%81%E7%BB%8F%E8%BF%87%E5%BE%AE%E4%BF%A1%E6%96%B9%E9%9D%A2%E7%9A%84%E5%AE%A1%E6%A0%B8 "citation")

> 说明：微信公众平台后台规则（mp.weixin.qq.com）与腾讯客服 FAQ（kf.qq.com）为最终执行口径；认证费用、域名数量限制、外链权限等细则近年有调整，操作前需以官方最新公告为准。
