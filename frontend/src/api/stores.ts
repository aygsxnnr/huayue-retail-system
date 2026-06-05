import request from './request';

export interface Store {
  id: number;
  code: string;
  name: string;
  city: string;
  address: string;
  manager: string;
  status: string;
}

export type StorePayload = Omit<Store, 'id'>;

export async function fetchStores() {
  const { data } = await request.get<Store[]>('/stores');
  return data;
}

export async function createStore(payload: StorePayload) {
  const { data } = await request.post<Store>('/stores', payload);
  return data;
}

export async function updateStore(id: number, payload: Partial<StorePayload>) {
  const { data } = await request.put<Store>(`/stores/${id}`, payload);
  return data;
}

export async function updateStoreStatus(id: number, status: string) {
  const { data } = await request.put<Store>(`/stores/${id}/status`, { status });
  return data;
}
