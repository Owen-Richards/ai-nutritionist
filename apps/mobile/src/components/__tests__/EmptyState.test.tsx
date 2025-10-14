import { fireEvent } from "@testing-library/react-native";

import { EmptyState } from "@/components/EmptyState";
import { renderWithProviders } from "@/test-utils/render";

describe("EmptyState", () => {
  it("renders fallback message", () => {
    const { getByText } = renderWithProviders(
      <EmptyState title="Nothing" message="No data" />
    );
    expect(getByText("Nothing")).toBeTruthy();
  });

  it("performs action when pressed", () => {
    const onAction = jest.fn();
    const { getByText } = renderWithProviders(
      <EmptyState title="Nothing" message="No data" actionLabel="Do something" onActionPress={onAction} />
    );
    fireEvent.press(getByText("Do something"));
    expect(onAction).toHaveBeenCalled();
  });
});
