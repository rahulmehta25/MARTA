# MARTA Frontend - Vercel Deployment Checklist

## ✅ Pre-Deployment Configuration

### 1. Build Configuration
- [x] **package.json**: Updated to use Vite instead of Create React App
- [x] **vite.config.ts**: Optimized for production builds with code splitting
- [x] **tsconfig.json**: Proper TypeScript configuration created
- [x] **tsconfig.node.json**: Node.js tooling configuration
- [x] **vercel.json**: SPA routing and build configuration

### 2. Dependencies
- [x] **Vite & TypeScript**: All build tools properly configured
- [x] **React 18+**: Modern React with proper TypeScript types
- [x] **UI Components**: Complete shadcn/ui component library
- [x] **Radix UI**: All necessary primitive components
- [x] **Routing**: React Router DOM for SPA routing

### 3. Environment Variables
- [x] **.env.example**: Template created for required variables
- [ ] **Production env vars**: Set in Vercel dashboard
  - `VITE_API_BASE_URL`
  - `VITE_APP_NAME`
  - `VITE_APP_VERSION`

## 🚀 Vercel Deployment Steps

### 1. Connect Repository
```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Link project (run from frontend/ directory)
vercel
```

### 2. Configure Build Settings
In Vercel Dashboard:
- **Framework Preset**: Vite
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`

### 3. Set Environment Variables
Navigate to: Project Settings > Environment Variables
```
VITE_API_BASE_URL=https://marta-production.up.railway.app
VITE_APP_NAME=MARTA Analytics Dashboard
VITE_APP_VERSION=1.0.0
```

### 4. Deploy
```bash
# Deploy to production
vercel --prod
```

## 🔍 Post-Deployment Verification

### Frontend Functionality
- [ ] Application loads without console errors
- [ ] React Router navigation works correctly
- [ ] All UI components render properly
- [ ] Responsive design works on mobile/desktop
- [ ] API calls are routed correctly (check Network tab)

### Performance Checks
- [ ] Initial page load < 3 seconds
- [ ] Lighthouse score > 90 for Performance
- [ ] No console warnings or errors
- [ ] Proper code splitting (check Network tab chunks)

### SEO & Accessibility  
- [ ] Meta tags populate correctly
- [ ] Open Graph tags work for social sharing
- [ ] Proper ARIA labels and semantic HTML
- [ ] Keyboard navigation functional

## 🛠️ Troubleshooting

### Common Issues

**Build Failures:**
- Check TypeScript errors: `npm run type-check`
- Verify all imports use correct paths
- Ensure all dependencies are installed

**Runtime Errors:**
- Check environment variables are set
- Verify API endpoints are accessible
- Check CORS configuration on backend

**Performance Issues:**
- Review bundle size: `npm run build` and check dist/ folder
- Optimize images and assets
- Enable gzip compression in Vercel

### Vercel-Specific

**Deployment Config:**
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite"
}
```

**SPA Routing Fix:**
Ensured in `vercel.json`:
```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

## 📊 Monitoring

### Analytics & Performance
- [ ] Set up Vercel Analytics
- [ ] Monitor Core Web Vitals
- [ ] Track user interactions
- [ ] Monitor API call success rates

### Error Tracking
- [ ] Implement error boundary components
- [ ] Set up error logging (Sentry, LogRocket, etc.)
- [ ] Monitor console errors in production

## 🔄 Continuous Deployment

### Automatic Deployments
- [x] **Main Branch**: Auto-deploy to production
- [x] **Feature Branches**: Auto-deploy to preview URLs
- [x] **Pull Requests**: Automatic preview deployments

### Quality Gates
- [ ] Set up GitHub Actions for:
  - TypeScript type checking
  - ESLint validation
  - Build verification
  - Performance testing

---

## 📝 Final Deployment Command

```bash
cd /Users/rahulmehta/Desktop/MARTA/frontend
vercel --prod
```

**Expected Output:**
```
✅  Production: https://marta-frontend-xxx.vercel.app [copied to clipboard]
```

The frontend is now fully configured and ready for Vercel deployment!