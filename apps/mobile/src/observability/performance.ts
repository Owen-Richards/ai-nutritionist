export const markAppStart = () => {
  if (globalThis.performance?.mark) {
    performance.mark("app:start");
  }
};

export const markAppReady = () => {
  if (globalThis.performance?.mark) {
    performance.mark("app:ready");
  }
};
