import { createContext, useContext } from "react";
import type {
  Account,
  Capability,
  LogEntry,
  MCPToken,
  Overview,
  Task,
} from "./lib/types";

export type Workspace = {
  user: string;
  page: string;
  navigate: (path: string) => void;
  accounts: Account[];
  accountId: string;
  setAccountId: (id: string) => void;
  selected?: Account;
  tasks: Task[];
  tokens: MCPToken[];
  logs: LogEntry[];
  catalog: Capability[];
  overview: Overview;
  busy: string;
  action: (name: string, fn: () => Promise<unknown>) => Promise<void>;
  openTask: (id: string) => Promise<void>;
  copy: (value: string) => Promise<void>;
  setNotice: (value: string) => void;
  setError: (value: string) => void;
  offset: number;
  setOffset: (value: number) => void;
  filter: string;
  setFilter: (value: string) => void;
  openAccountModal: () => void;
  openTokenModal: () => void;
  oneTime: string;
  setOneTime: (value: string) => void;
};

export const WorkspaceContext = createContext<Workspace | null>(null);

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used inside the shell");
  return value;
}
