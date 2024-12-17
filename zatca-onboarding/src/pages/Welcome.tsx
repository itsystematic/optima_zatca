import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { setCurrentPage } from "@/data/currentPage";
import { Button } from "antd";
import React from "react";
import MainPage from "./MainPage";

const Welcome: React.FC = () => {
  const dispatch = useAppDispatch();
  const currentPage = useAppSelector((state) => state.pageReducer.currentPage);

  const handleGetStarted = () => {
    dispatch(setCurrentPage(1));
  };

  return (
    <>
      {currentPage ? (
        <MainPage />
      ) : (
        <div
          className='relative transition-all duration-300 h-screen bg-cover object-cover'
        >
          <img
            className="bg-cover bg-center h-screen w-screen"
            src={`${
              isDev
                ? "Welcome.png"
                : "/assets/optima_zatca/zatca-onboarding/Welcome.png"
            }`}
          />
          <Button
            type="primary"
            onClick={handleGetStarted}
            className="absolute font-bold text-3xl top-[71%] left-[10%] rounded-md w-[263px] h-[78px] bg-[#07012f] hover:bg-[#483f61]"
          >
            Get Started
          </Button>
        </div>
      )}
    </>
  );
};

export default Welcome;
