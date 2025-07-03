// miniprogram/pages/chat/index.js
import { v4 as uuidv4 } from '../../utils/uuid';

Page({
  data: {
    user_id: '',
    session_id: '',
    messages: [],
    input: ''
  },
  onLoad() {
    // 获取/生成用户id
    let user_id = wx.getStorageSync('user_id');
    if (!user_id) {
      user_id = 'user_' + Math.random().toString(36).slice(2);
      wx.setStorageSync('user_id', user_id);
    }
    // 新会话id
    const session_id = uuidv4();
    this.setData({ user_id, session_id });
  },
  onInput(e) {
    this.setData({ input: e.detail.value });
  },
  sendMsg() {
    const { input, user_id, session_id, messages } = this.data;
    if (!input.trim()) return;
    this.setData({ messages: [...messages, { role: 'user', content: input }], input: '' });
    wx.request({
      url: 'http://localhost:8000/chat/qa', // 替换为你的后端地址
      method: 'POST',
      data: { question: input, user_id, session_id },
      success: (res) => {
        const answer = res.data.answer;
        this.setData({ messages: [...this.data.messages, { role: 'assistant', content: answer }] });
      },
      fail: () => {
        this.setData({ messages: [...this.data.messages, { role: 'assistant', content: '网络错误，请稍后重试。' }] });
      }
    });
  }
});
