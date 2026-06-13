import { Button, Card, Input, Select, Space, Table, Tag, Typography, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useEffect, useState } from 'react';
import { listOperationLogs } from '../api/operationLogs';
import type { OperationLogItem } from '../api/operationLogs';

export default function OperationLog() {
  const [logs, setLogs] = useState<OperationLogItem[]>([]);
  const [keyword, setKeyword] = useState('');
  const [module, setModule] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await listOperationLogs({
        keyword: keyword || undefined,
        module,
        limit: 200
      });
      setLogs(data);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作日志读取失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchLogs();
  }, []);

  const columns: ColumnsType<OperationLogItem> = [
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 190,
      render: (value: string) => value ? new Date(value).toLocaleString() : '-'
    },
    {
      title: '操作人',
      dataIndex: 'operator_name',
      width: 120
    },
    {
      title: '角色',
      dataIndex: 'role',
      width: 130,
      render: (role: string) => <Tag color="blue">{role}</Tag>
    },
    {
      title: '模块',
      dataIndex: 'module',
      width: 120
    },
    {
      title: '动作',
      dataIndex: 'action',
      width: 130
    },
    {
      title: '对象',
      width: 160,
      render: (_, record) => `${record.target_type || '-'} #${record.target_id || '-'}`
    },
    {
      title: '变更前',
      dataIndex: 'before_data',
      width: 260,
      ellipsis: true,
      render: (value: string) => value || '-'
    },
    {
      title: '变更后',
      dataIndex: 'after_data',
      width: 260,
      ellipsis: true,
      render: (value: string) => value || '-'
    },
    {
      title: '备注',
      dataIndex: 'remark',
      width: 220,
      ellipsis: true,
      render: (value: string) => value || '-'
    }
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <div>
        <Typography.Title level={3} style={{ marginBottom: 4 }}>
          操作日志审计
        </Typography.Title>
        <Typography.Text type="secondary">
          查看用户管理、权限维护等关键操作记录。
        </Typography.Text>
      </div>

      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Input.Search
            placeholder="搜索操作人、动作、对象、备注"
            allowClear
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            onSearch={() => fetchLogs()}
            style={{ width: 300 }}
          />

          <Select
            allowClear
            placeholder="选择模块"
            value={module}
            onChange={(value) => setModule(value)}
            style={{ width: 180 }}
            options={[
              { label: '用户管理', value: '用户管理' },
              { label: '门店管理', value: '门店管理' },
              { label: '商品管理', value: '商品管理' },
              { label: '财务对账', value: '财务对账' },
              { label: '会员营销', value: '会员营销' }
            ]}
          />

          <Button type="primary" onClick={() => fetchLogs()}>
            查询
          </Button>
        </Space>

        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={logs}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1500 }}
        />
      </Card>
    </Space>
  );
}
