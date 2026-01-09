# FlashDash Desktop App

Electron desktop application for flashing GrapheneOS.

## Environment Configuration

The application uses environment variables for configuration. Create a `.env` file in this directory (copy from `.env.example`):

```bash
cp .env.example .env
```

### Available Environment Variables

- `VITE_API_BASE_URL` - Backend API base URL (default: `http://127.0.0.1:17890`)

Example `.env` file:
```env
VITE_API_BASE_URL=http://127.0.0.1:17890
```

For production:
```env
VITE_API_BASE_URL=https://api.example.com
```

**Note**: Environment variables must be prefixed with `VITE_` to be exposed to the client-side code in Vite applications.

## Development

```bash
# Install dependencies
pnpm install

# Run in development mode
pnpm dev
```

## Building

```bash
# Build for production
pnpm build
```

Outputs to `out/` directory.

