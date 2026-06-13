import request from './request';

export type CurrentUser = {
  id: number;
  username: string;
  real_name: string;
  role: string;
  store_id: number | null;
  status: string;
  created_at?: string;
  updated_at?: string;
};

export type LoginParams = {
  username: string;
  password: string;
};

export type LoginResponse = {
  token: string;
  user: CurrentUser;
};

export async function login(params: LoginParams) {
  const response = await request.post<LoginResponse>('/auth/login', params);
  return response.data;
}

export async function getCurrentUser() {
  const response = await request.get<{ user: CurrentUser }>('/auth/me');
  return response.data.user;
}

export async function logout() {
  const response = await request.post('/auth/logout');
  return response.data;
}

export function getDefaultPathByRole(role: string) {
  const pathMap: Record<string, string> = {
    系统管理员: '/dashboard',
    总经理: '/dashboard',
    店长: '/pos',
    收银员: '/pos',
    库存管理员: '/inventory',
    营销专员: '/members',
    财务人员: '/finance'
  };

  return pathMap[role] || '/dashboard';
}
