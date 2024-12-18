import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { setCurrentPage } from "@/data/currentPage";
import { setStep } from "@/data/currentStep";
import { resetData } from "@/data/dataSlice";
import { LeftOutlined } from "@ant-design/icons";
import { ConfigProvider, Flex } from "antd";
import React from "react";

const CustomModal: React.FC<React.PropsWithChildren> = ({ children }) => {
  const dispatch = useAppDispatch();
  const currentPage = useAppSelector((state) => state.pageReducer.currentPage);

  const handleBackButton = () => {
    dispatch(setCurrentPage(currentPage - 1));
    dispatch(setStep({ currentStep: 0 }));
    dispatch(resetData());
  };
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#483f61", // Custom primary color
        },
        components: {
          Input: {
            controlHeightLG: 48,
            marginLG: 0,
          },
          Button: {
            controlHeightLG: 48,
          },
        },
      }}
    >
      <Flex
        align="center"
        justify="center"
        className="h-full w-full bg-cover bg-no-repeat"
      >
        <img
          src={
            isDev
              ? "Tutorial.png"
              : "/assets/optima_zatca/zatca-onboarding/Tutorial.png"
          }
          alt="Background"
          className="absolute top-0 left-0 h-full w-full bg-cover"
        />
        <Flex
          vertical
          className="h-[80vh] w-[65vw] p-2 bg-[#483f6140] relative"
        >
          <div>
            <LeftOutlined
              onClick={handleBackButton}
              className={`transition-all duration-300 cursor-pointer hover:bg-gray-400 hover:rounded p-2 ${
                currentPage === 200 && "hidden"
              }`}
            />
          </div>
          {children}
        </Flex>
      </Flex>
    </ConfigProvider>
  );
};

export default CustomModal;
