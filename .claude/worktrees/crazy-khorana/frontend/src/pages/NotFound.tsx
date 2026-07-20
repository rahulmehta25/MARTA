import { useLocation, Link } from "react-router-dom";
import { useEffect } from "react";
import { MapPin, ArrowLeft } from "lucide-react";

const NotFound = () => {
  const location = useLocation();

  useEffect(() => {
    console.error(
      "404 Error: User attempted to access non-existent route:",
      location.pathname
    );
  }, [location.pathname]);

  return (
    <div id="not-found-page" className="min-h-screen flex items-center justify-center bg-background">
      <div id="not-found-content" className="text-center px-6">
        <div id="not-found-icon" className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-full mb-6">
          <MapPin className="h-8 w-8 text-primary" aria-hidden="true" />
        </div>
        <h1 className="text-5xl font-bold text-foreground mb-2">404</h1>
        <p className="text-lg text-muted-foreground mb-6">
          This stop doesn't exist on the route.
        </p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to Map
        </Link>
      </div>
    </div>
  );
};

export default NotFound;
