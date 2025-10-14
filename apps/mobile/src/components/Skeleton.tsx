import React from "react";
import { Animated, Easing, StyleProp, StyleSheet, View, ViewProps, ViewStyle } from "react-native";

import { useTheme } from "@/providers/ThemeProvider";

type SkeletonProps = ViewProps & {
  width?: number | string;
  height?: number;
  radius?: number;
  style?: StyleProp<ViewStyle>;
};

const AnimatedView = Animated.createAnimatedComponent(View);

export const Skeleton: React.FC<SkeletonProps> = ({ width = "100%", height = 16, radius, style, ...rest }) => {
  const { colors, radius: themeRadius } = useTheme();
  const animated = React.useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(animated, {
          toValue: 1,
          duration: 900,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true
        }),
        Animated.timing(animated, {
          toValue: 0,
          duration: 900,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true
        })
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [animated]);

  const backgroundColor = colors.skeletonBase;
  const highlightColor = colors.skeletonHighlight;

  const animatedStyle = {
    opacity: animated.interpolate({ inputRange: [0, 1], outputRange: [0.7, 1] })
  };

  return (
    <AnimatedView
      style={[
        styles.base,
        {
          width,
          height,
          borderRadius: radius ?? themeRadius.sm,
          backgroundColor
        },
        animatedStyle,
        style
      ]}
      {...rest}
    >
      <AnimatedView style={[StyleSheet.absoluteFill, { backgroundColor: highlightColor, opacity: 0.25, borderRadius: radius ?? themeRadius.sm }]} />
    </AnimatedView>
  );
};

export const SkeletonLines: React.FC<{ lines?: number; spacing?: number; maxWidth?: number | string }> = ({
  lines = 3,
  spacing = 12,
  maxWidth = "100%"
}) => {
  const items = React.useMemo(() => Array.from({ length: lines }), [lines]);
  return (
    <View style={{ gap: spacing, width: maxWidth }}>
      {items.map((_, index) => (
        <Skeleton key={index} width={index === lines - 1 ? "70%" : "100%"} testID="skeleton" />
      ))}
    </View>
  );
};

export const SkeletonCircle: React.FC<{ size?: number; style?: StyleProp<ViewStyle> } & ViewProps> = ({ size = 48, style, ...rest }) => {
  return <Skeleton width={size} height={size} radius={size / 2} style={style} {...rest} />;
};

const styles = StyleSheet.create({
  base: {
    overflow: "hidden"
  }
});
