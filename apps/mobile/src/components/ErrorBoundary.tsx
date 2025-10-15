import React from "react";

import { ErrorState } from "@/components/ErrorState";
import { useAppTranslation } from "@/i18n";

export type ErrorBoundaryProps = {
  children: React.ReactNode;
  fallback?: (error: Error, reset: () => void) => React.ReactNode;
  onError?: (error: Error, info: React.ErrorInfo) => void;
};

type ErrorBoundaryState = {
  error: Error | null;
};

class Boundary extends React.Component<
  ErrorBoundaryProps & { defaultFallback: (error: Error, reset: () => void) => React.ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    if (this.props.onError) {
      this.props.onError(error, info);
    }
  }

  reset = () => {
    this.setState({ error: null });
  };

  render(): React.ReactNode {
    const { error } = this.state;
    const { children, fallback, defaultFallback } = this.props;
    if (error) {
      return (fallback ?? defaultFallback)(error, this.reset);
    }
    return children;
  }
}

export const ErrorBoundary: React.FC<ErrorBoundaryProps> = ({ children, fallback, onError }) => {
  const { t } = useAppTranslation("common");

  const defaultFallback = React.useCallback(
    (error: Error, reset: () => void) => (
      <ErrorState
        title={t("states.error")}
        message={error.message || t("errors.generic")}
        onRetry={reset}
        primaryActionLabel={t("actions.retry")}
      />
    ),
    [t]
  );

  return (
    <Boundary defaultFallback={defaultFallback} fallback={fallback} onError={onError}>
      {children}
    </Boundary>
  );
};
