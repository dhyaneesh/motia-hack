import { config } from 'motia'

export default config({
  plugins: [],
  // Using external Memurai/Redis instance
  redis: {
    useMemoryServer: false,
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
    password: process.env.REDIS_PASSWORD,
    username: process.env.REDIS_USERNAME,
    db: parseInt(process.env.REDIS_DB || '0'),
  },
})
