import { PlusOutlined } from '@ant-design/icons';
import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useEffect, useState } from 'react';
import {
  createUser,
  listRoles,
  listUsers,
  updateUser,
  updateUserStatus
} from '../api/users';
import type { RoleItem, UserCreatePayload, UserItem, UserUpdatePayload } from '../api/users';

type UserFormValues = {
  username: string;
  password?: string;
  real_name: string;
  role: string;
  store_id?: number | null;
  status: string;
};

export default function UserPermission() {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserItem | null>(null);
  const [form] = Form.useForm<UserFormValues>();

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const data = await listUsers(keyword);
      setUsers(data);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '用户列表读取失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchRoles = async () => {
    try {
      const data = await listRoles();
      setRoles(data);
    } catch {
      setRoles([]);
    }
  };

  useEffect(() => {
    void fetchUsers();
    void fetchRoles();
  }, []);

  const openCreateModal = () => {
    setEditingUser(null);
    form.resetFields();
    form.setFieldsValue({
      status: '启用',
      role: '收银员'
    });
    setModalOpen(true);
  };

  const openEditModal = (record: UserItem) => {
    setEditingUser(record);
    form.setFieldsValue({
      username: record.username,
      password: '',
      real_name: record.real_name,
      role: record.role,
      store_id: record.store_id,
      status: record.status
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();

    const commonPayload = {
      real_name: values.real_name,
      role: values.role,
      store_id: values.store_id ?? null,
      status: values.status
    };

    try {
      if (editingUser) {
        const payload: UserUpdatePayload = { ...commonPayload };
        if (values.password) {
          payload.password = values.password;
        }
        await updateUser(editingUser.id, payload);
        message.success('用户已更新');
      } else {
        const payload: UserCreatePayload = {
          username: values.username,
          password: values.password || '123456',
          ...commonPayload
        };
        await createUser(payload);
        message.success('用户已新增');
      }

      setModalOpen(false);
      await fetchUsers();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败');
    }
  };

  const handleStatusChange = async (record: UserItem) => {
    const nextStatus = record.status === '启用' ? '停用' : '启用';

    try {
      await updateUserStatus(record.id, nextStatus);
      message.success(`用户已${nextStatus}`);
      await fetchUsers();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '状态更新失败');
    }
  };

  const columns: ColumnsType<UserItem> = [
    {
      title: '用户名',
      dataIndex: 'username',
      width: 130
    },
    {
      title: '姓名',
      dataIndex: 'real_name',
      width: 140
    },
    {
      title: '角色',
      dataIndex: 'role',
      width: 150,
      render: (role: string) => <Tag color="blue">{role}</Tag>
    },
    {
      title: '门店ID',
      dataIndex: 'store_id',
      width: 100,
      render: (storeId: number | null) => storeId ?? '-'
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={status === '启用' ? 'green' : 'red'}>{status}</Tag>
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 190,
      render: (value: string) => value ? new Date(value).toLocaleString() : '-'
    },
    {
      title: '操作',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => openEditModal(record)}>
            编辑
          </Button>
          <Popconfirm
            title={`确认${record.status === '启用' ? '停用' : '启用'}该用户？`}
            onConfirm={() => handleStatusChange(record)}
          >
            <Button type="link" danger={record.status === '启用'}>
              {record.status === '启用' ? '停用' : '启用'}
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <div>
        <Typography.Title level={3} style={{ marginBottom: 4 }}>
          用户管理与角色权限
        </Typography.Title>
        <Typography.Text type="secondary">
          管理系统账号、角色、门店归属与启停状态。
        </Typography.Text>
      </div>

      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Input.Search
            placeholder="搜索用户名、姓名、角色、状态"
            allowClear
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            onSearch={() => fetchUsers()}
            style={{ width: 280 }}
          />
          <Button onClick={() => fetchUsers()}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
            新增用户
          </Button>
        </Space>

        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={users}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1100 }}
        />
      </Card>

      <Modal
        title={editingUser ? '编辑用户' : '新增用户'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="用户名"
            name="username"
            rules={[{ required: !editingUser, message: '请输入用户名' }]}
          >
            <Input disabled={!!editingUser} placeholder="例如：admin" />
          </Form.Item>

          <Form.Item
            label={editingUser ? '新密码（不填则不修改）' : '密码'}
            name="password"
            rules={[{ required: !editingUser, message: '请输入密码' }]}
          >
            <Input.Password placeholder="默认建议 123456" />
          </Form.Item>

          <Form.Item
            label="真实姓名"
            name="real_name"
            rules={[{ required: true, message: '请输入真实姓名' }]}
          >
            <Input placeholder="例如：张三" />
          </Form.Item>

          <Form.Item
            label="角色"
            name="role"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select
              options={roles.map((role) => ({
                label: role.label,
                value: role.value
              }))}
            />
          </Form.Item>

          <Form.Item label="门店ID" name="store_id">
            <InputNumber style={{ width: '100%' }} placeholder="可为空，例如 1" min={1} />
          </Form.Item>

          <Form.Item
            label="状态"
            name="status"
            rules={[{ required: true, message: '请选择状态' }]}
          >
            <Select
              options={[
                { label: '启用', value: '启用' },
                { label: '停用', value: '停用' }
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}
