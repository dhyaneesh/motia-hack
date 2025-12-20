import { Providers } from './providers';

export const metadata = {
  title: 'Knowledge Graph Chatbot',
  description: 'Interactive knowledge graph visualization with LLM-powered search',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

