import request from './request';

export type OperationLogItem = {
  id: number;
  operator_id: number | null;
  operator_name: string;
  role: string;
  module: string;
  action: string;
  target_type: string;
  target_id: string;
  before_data: string;
  after_data: string;
  created_at: string;
  remark: string;
};

export type OperationLogQuery = {
  module?: string;
  keyword?: string;
  limit?: number;
};

export async function listOperationLogs(params?: OperationLogQuery) {
  const response = await request.get<OperationLogItem[]>('/operation-logs', {
    params
  });
  return response.data;
}
