import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App.tsx";
import { AuthProvider } from "./context/AuthContext";
import { ToastStack, type ToastItem } from "./components/ui/Toast";
import { ApiError } from "./api/client";
import "./styles/tokens.css";
import "./index.css";

function toastMessageFromError(error: unknown): { message: string; tone: ToastItem["tone"] } {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "forbidden":
        return { message: "You don't have permission for this action.", tone: "warning" };
      case "conflict":
      case "business_rule_violation":
        return { message: error.message, tone: "warning" };
      case "validation_error":
        return { message: error.message, tone: "critical" };
      case "internal_error":
        return { message: "Something went wrong, please try again.", tone: "critical" };
      default:
        return { message: error.message, tone: "critical" };
    }
  }
  return { message: "Something went wrong, please try again.", tone: "critical" };
}

function Root() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const pushToast = (message: string, tone: ToastItem["tone"] = "info") => {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev, { id, message, tone }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  };

  const [queryClient] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({
          onError: (error) => {
            if (error instanceof ApiError && (error.code === "unauthorized" || error.status === 401)) {
              return;
            }
            if (error instanceof ApiError && error.code === "not_found") {
              return;
            }
          },
        }),
        mutationCache: new MutationCache({
          onError: (error) => {
            if (error instanceof ApiError && error.code === "unauthorized") return;
            if (error instanceof ApiError && error.code === "validation_error") return;
            const { message, tone } = toastMessageFromError(error);
            pushToast(message, tone);
          },
        }),
        defaultOptions: {
          queries: {
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <App />
          <ToastStack toasts={toasts} onDismiss={(id) => setToasts((t) => t.filter((x) => x.id !== id))} />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
