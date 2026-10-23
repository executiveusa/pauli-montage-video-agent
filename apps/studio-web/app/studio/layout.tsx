// The workspace shell is public so browser-local projects need no account.
// Hosted project data and media remain protected by studio-proxy on every API request.
export default function StudioLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return children;
}
