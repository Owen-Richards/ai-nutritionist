const config = require("jest-expo/config").default(__dirname);

module.exports = {
  ...config,
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1"
  },
  testMatch: ["**/__tests__/**/*.test.(ts|tsx)", "**/?(*.)+(spec|test).(ts|tsx)"]
};
