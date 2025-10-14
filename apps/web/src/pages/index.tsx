import Head from "next/head";
import { Button } from "@ai-health/ui";

export default function HomePage() {
  return (
    <>
      <Head>
        <title>AI Nutritionist Portal</title>
      </Head>
      <main style={styles.main}>
        <section style={styles.hero}>
          <h1 style={styles.title}>AI Nutritionist Web Console</h1>
          <p style={styles.subtitle}>
            This web experience will surface dashboards, plan editors, and health integration settings that
            complement the chat-first assistant.
          </p>
          <Button onPress={() => {}}>Coming Soon</Button>
        </section>
      </main>
    </>
  );
}

const styles: Record<string, React.CSSProperties> = {
  main: {
    minHeight: "100vh",
    display: "grid",
    placeItems: "center",
    background: "#f8fafc",
    padding: "48px"
  },
  hero: {
    maxWidth: "720px",
    background: "#ffffff",
    borderRadius: "24px",
    padding: "40px",
    boxShadow: "0 20px 45px rgba(15, 23, 42, 0.08)",
    textAlign: "center"
  },
  title: {
    fontSize: "2.5rem",
    marginBottom: "12px",
    color: "#0f172a"
  },
  subtitle: {
    fontSize: "1.125rem",
    lineHeight: "1.8",
    color: "#475569",
    marginBottom: "32px"
  }
};
