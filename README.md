来实现一个添加好友功能，添加后好友会出现在对面的FriendList中
后端为 FriendList 提供的数据需求（列表接口建议：GET /api/friends，或在登录后下发）：
每个好友项需要的字段
id: 唯一标识
name 或 display_name: 用于列表显示的名称（可直接用用户的 avatar_name || username）
avatar: 头像 URL
lastMessage: 最近一条消息摘要（字符串）
online: 是否在线（布尔）
unread: 未读消息数（数字，0 也要返回）
可选字段（如后续用）
lastMessageTime: 最近消息时间（用于排序）
status: 自定义状态（active 等），可不必前端必填
返回示例
{  "success": true,  "data": [    {      "id": "user_123",      "name": "Alice",              // 或 display_name: "Alice"      "avatar": "https://...",      "lastMessage": "你好",      "online": true,      "unread": 2,      "lastMessageTime": "2025-01-01T10:00:00Z"    }  ]}
服务器侧建议
名称字段：直接返回 display_name = avatar_name || username，避免前端再次拼装。
未读计数：按照当前登录用户统计；没有未读返回 0。
排序：后端可按 lastMessageTime DESC 排序，前端可直接渲染。
在线状态：有实时能力可返回实时状态；没有可用 false 或最近一次在线时间。