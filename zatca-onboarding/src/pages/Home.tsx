import { useAppDispatch } from "@/app/hooks";
import Loading from "@/components/Loading";
import React, { useState } from "react";
import Welcome from "./Welcome";

const Home: React.FC = () => {
  const dispatch = useAppDispatch();
  const [data, setData] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);

  return (
    <div className="h-screen w-full">
      {/* Show loading screen */}
      {loading ? (
        <Loading />
      ) : data ? (
        // Show list view if data is loaded
        <div>List View</div>
      ) : (
        // Page sliding view
        <Welcome />
      )}
    </div>
  );
};

export default Home;
