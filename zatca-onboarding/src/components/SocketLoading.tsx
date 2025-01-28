import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { setCurrentPage } from "@/data/currentPage";
import { ReloadOutlined } from "@ant-design/icons";
import { Button, Flex, Progress } from "antd";
import { useEffect, useState } from "react";

const SocketLoading = () => {
  const [realTimeData, setRealTimeData] = useState<any>({});
  const dataState = useAppSelector((state) => {
    return {
      ...state.dataReducer,
      commercial_register: state.dataReducer.commercial_register.filter(
        (i) => !i.phase
      ),
    };
  });
  const [error, setError] = useState<boolean>();
  const dispatch = useAppDispatch();
  
  const totalCrCount = dataState.commercial_register.filter(
    (c) => !c.phase
  ).length;

  const completedCrCount = dataState.commercial_register.filter((cr) => {
    const crData = realTimeData[cr.commercial_register_number];
    return crData?.complete && crData?.indicator === "green"; // Completed CR
  }).length;
  
  const currentCommercial = dataState.commercial_register.find((cr) => {
    const crData = realTimeData[cr.commercial_register_number];
    return crData && !crData.complete; // Ensure we're finding CRs that are in progress
  });

  const currentPercentage = currentCommercial
    ? realTimeData[currentCommercial.commercial_register_number]?.percentage
    : 0; // If no CR is found, set default to 0

  const remainingCrCount = totalCrCount - completedCrCount;

  const isError = (cr: any) => {
    const data = realTimeData[cr.commercial_register_number];
    if (data && data.complete && data.indicator === "red") {
      frappe.realtime.off("zatca");
      setError(true);
      return;
    }
    setError(false);
  };

  const handleRetry = async () => {
    setError(false);
    ActivateIO();
    await frappe.call({
      method: "optima_zatca.zatca.api.register_company",
      args: dataState,
    });
  };

  const ActivateIO = () => {
    frappe.realtime.on("zatca", (data: any) => {
      console.log(data);
      if (data.commercial_register_name) {
        setRealTimeData((prevData: any) => ({
          ...prevData,
          [data.commercial_register_name]: data,
        }));
      }
    });
  };

  useEffect(() => {
    if (isDev) return;
    ActivateIO();
    const apiCall = async () => {
      try {
        if (isDev) {
          dispatch(setCurrentPage(204));
          return;
        }
        await frappe.call({
          method: "optima_zatca.zatca.api.register_company",
          args: dataState,
        });
      } catch (err) {
        setError(true);
      }
    };

    apiCall();
  }, []);

  useEffect(() => {
    if (!remainingCrCount) {
      if (completedCrCount === totalCrCount) {
        dispatch(setCurrentPage(200));
      } else {
        isError(currentCommercial);
      }
    }
  }, [remainingCrCount]);

  return (
    <div className="flex justify-between w-full h-full flex-col">
      <Flex
        gap={3}
        justify="center"
        align="center"
        className="h-full w-full"
        vertical
      >
        {/* Single Progress Bar */}
        <Progress
          status={
            completedCrCount === totalCrCount
              ? "success"
              : remainingCrCount > 0
              ? "active"
              : "exception"
          }
          className="text-[10px] w-full text-[#f3f3f3]"
          percent={currentPercentage} // Overall progress
          percentPosition={{ align: "center", type: "inner" }}
          size={{ height: 50 }}
          strokeColor="#483f61"
          format={() =>
            remainingCrCount > 0
              ? dataState.commercial_register[completedCrCount]
                  .commercial_register_name
              : "Successfully integerated with Zatca..."
          }
        />
        {currentCommercial && error ? (
          <div className="my-2">
            <Button onClick={handleRetry} className="bg-[#f3f3f3]">
              Try Again
              <ReloadOutlined />
            </Button>
          </div>
        ) : null}
        {/* Summary: Total, Completed, Remaining CRs */}
      </Flex>
      <div className="w-full flex justify-center">
        <div className="bg-[#483f61] w-fit text-[#f3f3f3] font-bold flex justify-center items-center gap-8 p-5 rounded-md">
          <p className="text-lg">
            {completedCrCount} / {totalCrCount} CRs completed
          </p>
        </div>
      </div>
    </div>
  );
};

export default SocketLoading;
