import { IconAlertTriangle, IconFileOff, IconLoader2 } from "@tabler/icons-react";

export function FilePreviewStatus({
  message,
  role,
  tone = "info",
}: {
  message: string;
  role?: "alert" | "status";
  tone?: "error" | "info" | "loading";
}) {
  const StatusIcon = tone === "loading" ? IconLoader2 : tone === "error" ? IconAlertTriangle : IconFileOff;
  return (
    <div className={`universal-file-preview__state universal-file-preview__state--${tone}`} role={role}>
      <span className="universal-file-preview__state-icon" aria-hidden>
        <StatusIcon className={tone === "loading" ? "is-spinning" : undefined} size={25} stroke={1.7} />
      </span>
      <p>{message}</p>
    </div>
  );
}
