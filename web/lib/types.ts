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
  /** Question utilisateur associée (pour le bouton Transmettre). */
  sourceQuestion?: string;
};
