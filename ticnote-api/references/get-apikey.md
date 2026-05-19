# API Key 获取指南

## 前提条件

- 已注册 TicNote 平台账号
- 账号已完成实名认证（如需要）

## 获取步骤

1. **登录 TicNote 平台**
   - 国内版：访问 `https://www.ticnote.cn`
   - 海外版：访问 `https://www.ticnote.com`

2. **进入设置页面**
   - 点击右上角头像 → 选择「账户设置」

3. **打开 API 管理页面**
   - 在左侧菜单中选择「API 密钥」或「开发者设置」

4. **创建 API Key**
   - 点击「新建密钥」按钮
   - 填写密钥名称（便于后续管理，如 "我的项目"）
   - 选择权限范围（建议按需选择最小权限）
   - 点击「确认创建」

5. **保存 API Key**
   - 创建成功后，页面会显示完整的 API Key
   - ⚠️ **API Key 仅显示一次**，请立即复制并妥善保存
   - 如果丢失需要重新创建

## API Key 格式

AppKey 根据环境不同有以下前缀：

| 前缀 | 说明 |
|------|------|
| `tncn_sk_` | 国内正式环境 |
| `tncn_sit_sk_` | 国内 SIT 测试环境 |
| `tnovs_sk_` | 海外正式环境 |
| `tnovs_sit_sk_` | 海外 SIT 测试环境 |

示例：
```
tncn_sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
tnovs_sk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 注意事项

| 事项 | 说明 |
|------|------|
| **安全存储** | 不要将 API Key 提交到代码仓库或公开分享 |
| **权限控制** | 按需分配最小权限，避免使用全权限 Key |
| **定期轮换** | 建议每 90 天更换一次 API Key |
| **删除旧 Key** | 不再使用的 Key 应及时删除 |
