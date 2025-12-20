import { Providers } from './providers';

export const metadata = {
  title: 'Dive - Searching Redefined',
  description: 'Dive: Visual search redefined. Explore knowledge through interactive graphs, shop with visual product discovery, and learn with structured concept hierarchies.',
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

