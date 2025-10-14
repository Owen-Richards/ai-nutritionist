import { renderWithProviders } from "@/test-utils/render";
import { Skeleton, SkeletonLines } from "@/components/Skeleton";
import { screen } from "@testing-library/react-native";

describe("Skeleton", () => {
  it("renders with provided dimensions", () => {
    renderWithProviders(<Skeleton testID="skeleton" width={120} height={12} />);
    expect(screen.getByTestId("skeleton")).toBeTruthy();
  });

  it("renders multiple lines", () => {
    renderWithProviders(<SkeletonLines lines={3} />);
    expect(screen.getAllByTestId("skeleton").length).toBeGreaterThan(0);
  });
});
