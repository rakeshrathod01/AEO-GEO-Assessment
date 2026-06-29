import { NavLink } from "react-router-dom";
import {
  Settings as SettingsIcon,
  LayoutDashboard,
  Gauge,
  FileText,
  Link2,
  ExternalLink,
  Search,
  Bot,
  MessageSquare,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { MODULES } from "@/lib/modules";
import { cn } from "@/lib/utils";

const ICONS: Record<string, LucideIcon> = {
  technical_seo: Gauge,
  on_page: FileText,
  internal_linking: Link2,
  backlinks: ExternalLink,
  keyword_universe: Search,
  aeo_audit: Bot,
  prompt_identification: MessageSquare,
  geo_audit: Sparkles,
  leadership: LayoutDashboard,
};

const linkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
    isActive
      ? "bg-eclerx-red/15 font-medium text-white shadow-[inset_2px_0_0_0_#e4002b]"
      : "text-slate-400 hover:bg-navy-800 hover:text-slate-100",
  );

export function Sidebar() {
  return (
    <aside className="flex h-screen w-64 flex-col border-r border-navy-800 bg-navy-900">
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="h-7 w-1.5 rounded-full bg-eclerx-red" />
        <div>
          <div className="text-lg font-bold tracking-tight text-white">eClerx</div>
          <div className="text-[11px] uppercase tracking-wider text-slate-500">
            SEO · AEO · GEO
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3">
        {MODULES.map((m) => {
          const Icon = ICONS[m.key] ?? FileText;
          return (
            <NavLink key={m.key} to={`/modules/${m.key}`} className={linkClass}>
              <Icon size={18} />
              <span className="flex-1">{m.title}</span>
              <span className="text-[10px] uppercase text-slate-600">{m.layer}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="border-t border-navy-800 p-3">
        <NavLink to="/settings" className={linkClass}>
          <SettingsIcon size={18} />
          Settings
        </NavLink>
      </div>
    </aside>
  );
}
