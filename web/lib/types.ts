export type Source = {
  chunk_id?: number | null;
  document: string;
  section: string;
  page: number | string | null;
  extrait: string;
  url?: string | null;
  /** absent/interne → bleu ; "web" → orange */
  type?: "interne" | "web";
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  latencyMs?: number;
  aRepondu?: boolean;
  file?: { id: string; filename: string };
};

export type DemoUser = {
  id: string;
  label: string;
  role: string;
  groups: string[];
};

export const DEMO_USERS: DemoUser[] = [
  { id: "marie", label: "Marie", role: "RH", groups: ["grp-rh", "grp-tous"] },
  { id: "paul", label: "Paul", role: "Commercial", groups: ["grp-tous"] },
];
