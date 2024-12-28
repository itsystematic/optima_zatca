import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { setCurrentPage } from "@/data/currentPage";
import { setStep } from "@/data/currentStep";
import { resetData } from "@/data/dataSlice";
import { closeTour, openTour } from "@/data/tour";
import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { ConfigProvider, Flex, Tooltip, Tour, Typography } from "antd";
import React from "react";

const CustomModal: React.FC<React.PropsWithChildren> = ({ children }) => {
  const dispatch = useAppDispatch();
  const currentPage = useAppSelector((state) => state.pageReducer.currentPage);
  const currentStep = useAppSelector((state) => state.stepReducer.currentStep);
  const tourState = useAppSelector((state) => state.tourReducer);
  const isAdding = useAppSelector((state) => state.addingReducer.isAdding);
  const lang = isDev ? "en" : frappe.boot.lang;

  const handleBackButton = () => {
    if (currentStep === 1 && isAdding) {
      dispatch(setStep({ currentStep: 0 }));
      dispatch(setCurrentPage(0));
      return;
    }
    if (currentStep === 1) {
      dispatch(setStep({ currentStep: 0 }));
      return;
    }
    if (currentStep === 2 && isAdding) {
      dispatch(setStep({ currentStep: 1 }));
      return;
    }
    dispatch(setCurrentPage(currentPage - 1));
    dispatch(setStep({ currentStep: 0 }));
    dispatch(resetData());
  };

  const handleHelper = () => {
    dispatch(openTour());
  };

  const onHelperClose = () => {
    dispatch(closeTour());
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
          Modal: {
            headerBg: "#f3f3f3",
            contentBg: "#f3f3f3",
          },
          Table: {
            headerBg: "#483f61",
            headerColor: "#ffffff",
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
          className="h-[80vh] w-[65vw] p-2 bg-[#483f6140] relative overflow-hidden"
        >
          <div className="h-[4%]">
            {lang === "ar" ? (
              <RightOutlined
                onClick={handleBackButton}
                className={`transition-all duration-300 cursor-pointer hover:bg-gray-400 hover:rounded p-2 ${
                  currentPage === 200 && "hidden"
                }`}
              />
            ) : (
              <LeftOutlined
                onClick={handleBackButton}
                className={`transition-all duration-300 cursor-pointer hover:bg-gray-400 hover:rounded p-2 ${
                  currentPage === 200 && "hidden"
                }`}
              />
            )}
          </div>
          <div className="h-[92%]">{children}</div>
          <div
            className={`flex justify-center items-center h-[4%] pb-[35px] gap-3 ${
              currentPage !== 4 && "hidden"
            }`}
          >
            <Typography.Text className="text-xl font-medium text-[#483f61] text-center">
              معلومات عن &nbsp;
              <Typography.Link
                target="_blank"
                href="https://www.optima.ae"
                className="text-xl font-medium"
              >
                موقع هيئه الذكاه
              </Typography.Link>
            </Typography.Text>
            <Tooltip
              placement={lang === 'ar' ? 'left' : 'right'}
              title="Click me if you need help!!"
              color="#483f61"
            >
              <img
                onClick={handleHelper}
                className="cursor-pointer bg-white border-[#483f61] border-2 rounded-full"
                src={
                  isDev
                    ? "MiniHelper.png"
                    : "/assets/optima_zatca/zatca-onboarding/MiniHelper.png"
                }
                alt="MiniHelper"
                height={50}
                width={50}
              />
            </Tooltip>
          </div>
        </Flex>
        <Tour
          key={tourState.steps.length}
          open={tourState.open}
          onClose={onHelperClose}
          steps={tourState.steps.map((step: any) => ({
            ...step,
            target: document.querySelector(`#${step.target}`), // Resolve dynamically
          }))}
        />
      </Flex>
    </ConfigProvider>
  );
};

export default CustomModal;
