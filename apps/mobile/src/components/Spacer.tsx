import React from "react";
import { View } from "react-native";

export const Spacer: React.FC<{ size?: number }> = ({ size = 16 }) => <View style={{ height: size }} />;
