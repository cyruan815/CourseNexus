import { IconFlask2 } from "@tabler/icons-react";
import { useEffect, useState } from "react";

import { getRuntimeStatus } from "../api/system";
import "./runtime-mode-banner.css";

export function RuntimeModeBanner() {
  const [mockModeEnabled, setMockModeEnabled] = useState(false);

  useEffect(() => {
    let active = true;

    void getRuntimeStatus()
      .then((status) => {
        if (active) {
          setMockModeEnabled(status.mock_model_provider_enabled);
        }
      })
      .catch(() => {
        // Runtime status must never block the application shell.
      });

    return () => {
      active = false;
    };
  }, []);

  if (!mockModeEnabled) {
    return null;
  }

  return (
    <div className="runtime-mode-banner" role="status" aria-live="polite">
      <span className="runtime-mode-banner__icon" aria-hidden="true">
        <IconFlask2 size={17} stroke={1.8} />
      </span>
      <span className="runtime-mode-banner__title">模拟模型模式</span>
      <span className="runtime-mode-banner__separator" aria-hidden="true" />
      <span className="runtime-mode-banner__description">
        当前生成内容仅用于开发验证
      </span>
    </div>
  );
}
