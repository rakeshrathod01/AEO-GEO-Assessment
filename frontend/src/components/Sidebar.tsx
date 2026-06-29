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

export function Sidebar() {
  return (
    <aside className="flex h-screen w-64 flex-col border-r border-slate-200 bg-white">
      <div className="px-5 py-5">
        <div className="text-lg font-semibold text-brand-dark">eClerx</div>
        <div className="text-xs text-slate-500">SEO · AEO · GEO Assessment</div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3">
        {MODULES.map((m) => {
          const Icon = ICONS[m.key] ?? FileText;
          return (
            <NavLink
              key={m.key}
              to={`/modules/${m.key}`}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-brand/10 font-medium text-brand"
                    : "text-slate-600 hover:bg-slate-100",
                )
              }
            >
              <Icon size={18} />
              <span className="flex-1">{m.title}</span>
              <span className="text-[10px] uppercase text-slate-400">{m.layer}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="border-t border-slate-200 p-3">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
              isActive ? "bg-brand/10 font-medium text-brand" : "text-slate-600 hover:bg-slate-100",
            )
          }
        >
          <SettingsIcon size={18} />
          Settings
        </NavLink>
      </div>
    </aside>
  );
}
