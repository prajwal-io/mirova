import type { NextConfig } from 'next';
const backend = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
if (!/^https?:\/\//.test(backend)) throw new Error('BACKEND_URL must be an HTTP URL.');
const config: NextConfig = {distDir:process.env.NEXT_DIST_DIR||'.next',poweredByHeader:false,output:'standalone',
 experimental:{proxyTimeout:240000},
 outputFileTracingExcludes:{'/*':['./.data/**','./.impeccable/**','./.next-test/**','./backend/**']},
 async rewrites(){return [{source:'/api/:path*',destination:`${backend}/api/:path*`}];},
 async headers(){return [{source:'/(.*)',headers:[{key:'X-Content-Type-Options',value:'nosniff'},{key:'Referrer-Policy',value:'strict-origin-when-cross-origin'},{key:'X-Frame-Options',value:'DENY'}]}];}
};
export default config;
