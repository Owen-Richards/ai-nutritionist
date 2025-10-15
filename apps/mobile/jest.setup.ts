import "@testing-library/jest-native/extend-expect";
jest.mock("@/hooks/useColorScheme", () => ({
  useColorScheme: () => "light"
}));

