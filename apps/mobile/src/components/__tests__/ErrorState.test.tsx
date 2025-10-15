import { fireEvent } from "@testing-library/react-native";

import { ErrorState } from "@/components/ErrorState";
import { renderWithProviders } from "@/test-utils/render";

describe("ErrorState", () => {
  it("fires retry callback", () => {
    const onRetry = jest.fn();
    const { getByText } = renderWithProviders(
      <ErrorState title="Error" message="Something went wrong" onRetry={onRetry} primaryActionLabel="Retry" />
    );
    fireEvent.press(getByText("Retry"));
    expect(onRetry).toHaveBeenCalled();
  });
});
