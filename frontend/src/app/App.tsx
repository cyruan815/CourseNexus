import { MantineProvider } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AppRouter } from "../router/AppRouter";
import { RuntimeModeBanner } from "../components/RuntimeModeBanner";
import "./theme.css";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MantineProvider>
        <ModalsProvider>
          <Notifications />
          <RuntimeModeBanner />
          <AppRouter />
        </ModalsProvider>
      </MantineProvider>
    </QueryClientProvider>
  );
}
