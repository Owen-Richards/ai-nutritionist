import { by, device, element } from "detox";

describe("navigation flow", () => {
  it("navigates across tabs", async () => {
    await device.launchApp({ delete: true });
    await element(by.id("quick-action-track"));
    await element(by.label("Plans")).tap();
    await element(by.label("Groceries")).tap();
    await element(by.label("Track")).tap();
  });
});
