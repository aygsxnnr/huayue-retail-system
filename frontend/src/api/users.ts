import request from './request';
import type { CurrentUser } from './auth';

export type UserItem = CurrentUser;

export type RoleItem = {
  label: string;
  value: string;
  menus: string[];
};

export type UserCreatePayload = {
  username: string;
  password: string;
  real_name: string;
  role: string;
  store_id?: number | null;
  status: string;
};

export type UserUpdatePayload = {
  password?: string;
  real_name?: string;
  role?: string;
  store_id?: number | null;
  status?: string;
};

export async function listRoles() {
  const response = await request.get<RoleItem[]>('/roles');
  return response.data;
}

export async function listUsers(keyword?: string) {
  const response = await request.get<UserItem[]>('/users', {
    params: keyword ? { keyword } : undefined
  });
  return response.data;
}

export async function createUser(payload: UserCreatePayload) {
  const response = await request.post<UserItem>('/users', payload);
  return response.data;
}

export async function updateUser(userId: number, payload: UserUpdatePayload) {
  const response = await request.put<UserItem>(`/users/${userId}`, payload);
  return response.data;
}

export async function updateUserStatus(userId: number, status: string) {
  const response = await request.put<UserItem>(`/users/${userId}/status`, { status });
  return response.data;
}
