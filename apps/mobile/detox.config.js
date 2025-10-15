module.exports = {
  testRunner: {
    args: {
      config: "e2e/jest.config.cjs"
    },
    type: "jest"
  },
  apps: {
    "ios.sim.release": {
      type: "ios.app",
      binaryPath: "bin/ios/Release-iphonesimulator/ai-health-mobile.app",
      build: "eas build --profile=detox --platform ios --local"
    }
  },
  devices: {
    "ios.sim": {
      type: "ios.simulator",
      device: {
        type: "iPhone 15"
      }
    }
  },
  configurations: {
    "ios.sim.release": {
      device: "ios.sim",
      app: "ios.sim.release"
    }
  }
};
