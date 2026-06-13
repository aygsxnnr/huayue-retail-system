import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { Button, Card, Form, Input, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDefaultPathByRole, login } from '../api/auth';
import type { LoginParams } from '../api/auth';

export default function LoginPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('huayue_token');
    const userText = localStorage.getItem('huayue_user');

    if (token && userText) {
      try {
        const user = JSON.parse(userText);
        navigate(getDefaultPathByRole(user.role), { replace: true });
      } catch {
        localStorage.removeItem('huayue_token');
        localStorage.removeItem('huayue_user');
      }
    }
  }, [navigate]);

  const handleLogin = async (values: LoginParams) => {
    setLoading(true);
    try {
      const data = await login(values);
      localStorage.setItem('huayue_token', data.token);
      localStorage.setItem('huayue_user', JSON.stringify(data.user));
      message.success('登录成功');
      navigate(getDefaultPathByRole(data.user.role), { replace: true });
    } catch (error: any) {
      message.error(error.response?.data?.detail || '登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #f4f7fb 0%, #e8f1ff 100%)',
        padding: 24
      }}
    >
      <Card
        style={{
          width: 420,
          borderRadius: 18,
          boxShadow: '0 18px 45px rgba(15, 35, 75, 0.12)'
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div
            style={{
              width: 64,
              height: 64,
              margin: '0 auto 16px',
              borderRadius: 18,
              background: '#1677ff',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 30,
              fontWeight: 700
            }}
          >
            悦
          </div>
          <Typography.Title level={3} style={{ marginBottom: 8 }}>
            华悦快时尚服饰有限公司
          </Typography.Title>
          <Typography.Text type="secondary">零售门店数字化管理系统</Typography.Text>
        </div>

        <Form layout="vertical" onFinish={handleLogin} initialValues={{ username: 'admin', password: '123456' }}>
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="请输入用户名" size="large" />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" size="large" />
          </Form.Item>

          <Button type="primary" htmlType="submit" size="large" block loading={loading}>
            登录
          </Button>
        </Form>

        <Typography.Paragraph type="secondary" style={{ marginTop: 20, marginBottom: 0, fontSize: 13 }}>
          测试账号：admin / 123456
        </Typography.Paragraph>
      </Card>
    </div>
  );
}
