import React, { useEffect, useRef, useState } from "react";
import Welcome from "./Welcome";

const Home: React.FC = () => {
  const [data, setData] = useState<boolean>(false);
  const tutorialPageRef = useRef<HTMLDialogElement>(null);
  const welcomePageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    tutorialPageRef.current?.showModal();
    const timer = setTimeout(() => {
      setData(true);
    }, 1000);

    return () => clearTimeout(timer)
  }, []);

  return (
    <div>
      {!data ? (
        <div>List View</div>
      ) : (
        <Welcome ref={welcomePageRef} />
      )}
    </div>
  );
};

export default Home;
