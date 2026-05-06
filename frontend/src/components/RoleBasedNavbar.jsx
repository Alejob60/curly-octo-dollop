import { motion } from "framer-motion";
import { ShieldCheck } from "lucide-react";
import { useI18n } from "../i18n";

const roleOptions = [
  "citizen",
  "front_desk",
  "lawyer",
  "reviewer",
  "secretary",
  "director",
  "mayor",
  "city_manager",
];

const moduleItems = [
  {
    key: "calilex_advisor",
    allowedRoles: ["citizen", "front_desk", "lawyer", "reviewer", "secretary", "director", "mayor", "city_manager"],
    color: "text-signal",
  },
  {
    key: "smart_ingest",
    allowedRoles: ["citizen", "front_desk"],
    color: "text-mist",
  },
  {
    key: "legal_desk",
    allowedRoles: ["lawyer", "reviewer"],
    color: "text-copper",
  },
  {
    key: "governance_flow",
    allowedRoles: ["secretary", "director"],
    color: "text-moss",
  },
  {
    key: "strategic_bi",
    allowedRoles: ["mayor", "city_manager"],
    color: "text-signal",
  },
];

export function RoleBasedNavbar({ role, onRoleChange, activeModule, onModuleChange }) {
  const { t } = useI18n();

  const visibleItems = moduleItems.filter((item) => item.allowedRoles.includes(role));

  return (
    <div className="rounded-[2rem] border border-white/10 bg-white/5 p-5 shadow-panel">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-signal/80">{t("rbac.navbarTitle")}</p>
          <h2 className="mt-2 flex items-center gap-2 font-display text-3xl text-mist">
            <ShieldCheck className="h-7 w-7 text-signal" />
            {t("rbac.navbarSubtitle")}
          </h2>
        </div>

        <label className="w-full max-w-sm">
          <span className="mb-2 block text-sm text-mist/60">{t("rbac.roleSelector")}</span>
          <select
            className="w-full rounded-2xl border border-white/10 bg-ink/70 px-4 py-3 text-mist"
            value={role}
            onChange={(event) => onRoleChange(event.target.value)}
          >
            {roleOptions.map((option) => (
              <option key={option} value={option}>
                {t(`rbac.role.${option}`)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <nav className="mt-5 flex flex-wrap gap-3">
        {visibleItems.map((item) => {
          const selected = item.key === activeModule;

          return (
            <button
              key={item.key}
              className={`relative overflow-hidden rounded-full border px-4 py-2 text-sm transition ${
                selected
                  ? "border-signal bg-signal text-ink"
                  : "border-white/15 bg-ink/60 text-mist/85 hover:border-signal/60"
              }`}
              onClick={() => onModuleChange(item.key)}
              type="button"
            >
              {selected && (
                <motion.span
                  className="absolute inset-0 -z-10 bg-signal"
                  layoutId="rbac-navbar-pill"
                  transition={{ duration: 0.25, ease: "easeOut" }}
                />
              )}
              <span className={selected ? "" : item.color}>{t(`rbac.module.${item.key}`)}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}