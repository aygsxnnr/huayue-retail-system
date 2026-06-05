import request from './request';
import type { Coupon } from './products';

export interface Member {
  id: number;
  member_no: string;
  name: string;
  phone: string;
  level: string;
  tags: string;
  member_tags: string[];
  available_coupons: string[];
  points: number;
  total_spent: number;
  total_orders: number;
  current_points?: number;
  total_amount?: number;
  total_times?: number;
  total_count?: number;
  cumulative_orders?: number;
  last_purchase_at?: string | null;
  last_purchase_date?: string | null;
  status: string;
  registered_store: string;
  joined_at: string;
}

export interface MemberPayload {
  name: string;
  phone: string;
  level?: string;
  tags?: string;
  points?: number;
  total_spent?: number;
  total_orders?: number;
  status?: string;
  registered_store?: string;
}

export interface MemberTagProfile {
  id: number;
  member_id: number;
  r_score: number;
  f_score: number;
  m_score: number;
  member_group: string;
  preference_tag: string;
  price_sensitive_tag: string;
  activity_tag: string;
  risk_tag: string;
  updated_at: string;
}

export interface MemberProfile {
  member: Member;
  tag_profile?: MemberTagProfile | null;
  recent_products: string[];
  preferred_categories: string[];
  recommended_actions: string[];
}

export interface RFMRecord {
  member_id: number;
  member_no: string;
  name: string;
  r_score: number;
  f_score: number;
  m_score: number;
  member_group: string;
  main_tags: string[];
  strategy: string;
}

export interface MarketingTouch {
  id: number;
  member_id: number;
  coupon_id?: number | null;
  promotion_id?: number | null;
  channel: string;
  touch_time: string;
  participation_status: string;
  writeoff_status: string;
  remark: string;
  member?: Member | null;
  coupon?: Coupon | null;
}

export interface MarketingTouchPayload {
  member_id: number;
  coupon_id?: number | null;
  promotion_id?: number | null;
  channel: string;
  participation_status?: string;
  writeoff_status?: string;
  remark?: string;
}

export interface RepurchaseRank {
  rank: number;
  member_id: number;
  member_no: string;
  name: string;
  total_orders: number;
  total_spent: number;
  last_purchase_at?: string | null;
  level: string;
  repurchase_tag: string;
}

export interface LevelDistribution {
  level: string;
  count: number;
}

export interface MarketingEffect {
  name: string;
  touched_count: number;
  clicked_count: number;
  participated_count: number;
  writeoff_count: number;
  writeoff_rate: number;
  driven_sales_amount: number;
}

export interface RepurchaseAnalysis {
  repurchase_ranking: RepurchaseRank[];
  level_distribution: LevelDistribution[];
  marketing_effects: MarketingEffect[];
}

export async function fetchMembers() {
  const { data } = await request.get<Member[]>('/members');
  return data;
}

export async function createMember(payload: MemberPayload) {
  const { data } = await request.post<Member>('/members', payload);
  return data;
}

export async function updateMember(id: number, payload: Partial<MemberPayload>) {
  const { data } = await request.put<Member>(`/members/${id}`, payload);
  return data;
}

export async function updateMemberStatus(id: number, status: string) {
  const { data } = await request.put<Member>(`/members/${id}/status`, { status });
  return data;
}

export async function fetchMemberProfile(id: number) {
  const { data } = await request.get<MemberProfile>(`/members/${id}/profile`);
  return data;
}

export async function fetchRfm() {
  const { data } = await request.get<RFMRecord[]>('/members/rfm');
  return data;
}

export async function recalculateRfm() {
  const { data } = await request.post<RFMRecord[]>('/members/rfm/recalculate');
  return data;
}

export async function fetchMarketingTouches() {
  const { data } = await request.get<MarketingTouch[]>('/members/marketing-touches');
  return data;
}

export async function createMarketingTouch(payload: MarketingTouchPayload) {
  const { data } = await request.post<MarketingTouch>('/members/marketing-touches', payload);
  return data;
}

export async function fetchRepurchaseAnalysis() {
  const { data } = await request.get<RepurchaseAnalysis>('/members/repurchase-analysis');
  return data;
}
