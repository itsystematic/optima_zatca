import { useAppDispatch, useAppSelector } from "@/app/hooks";
import { setCurrentPage } from "@/data/currentPage";
import { ReloadOutlined } from "@ant-design/icons";
import { Button, Flex, Progress } from "antd";
import { useEffect, useMemo, useState } from "react";

const SocketLoading = () => {
  const [realTimeData, setRealTimeData] = useState<any>({});
  const [error, setError] = useState<boolean>(false);
  const [failedCommercial, setFailedCommercial] = useState<any>(null);
  const dispatch = useAppDispatch();

  const dataState = useAppSelector((state) => ({
    ...state.dataReducer,
    commercial_register: state.dataReducer.commercial_register.filter((i) => !i.phase),
  }));

  const totalCrCount = dataState.commercial_register.length;

  const completedCrCount = dataState.commercial_register.filter((cr) => {
    const crData = realTimeData[cr.commercial_register_number];
    return crData?.complete && crData?.indicator === "green";
  }).length;

  const currentCommercial = useMemo(() => {
    return dataState.commercial_register.find((cr) => {
      const crData = realTimeData[cr.commercial_register_number];
      return crData && !crData.complete;
    });
  }, [realTimeData, dataState.commercial_register]);

  const currentPercentage = currentCommercial
    ? realTimeData[currentCommercial.commercial_register_number]?.percentage
    : 0;

  const remainingCrCount = totalCrCount - completedCrCount;

  const handleRetry = async () => {
    setError(false);
    setFailedCommercial(null);
    await frappe.call({
      method: "optima_zatca.zatca.api.register_company",
      args: dataState,
    });
  };

  useEffect(() => {
    if (isDev) return;

    frappe.realtime.on("zatca", (data: any) => {
      console.log(data);

      if (data.commercial_register_name) {
        setRealTimeData((prevData: any) => {
          const updated = {
            ...prevData,
            [data.commercial_register_name]: data,
          };

          const cr = dataState.commercial_register.find(
            (cr) => cr.commercial_register_number === data.commercial_register_name
          );

          if (cr && data.indicator === "red") {
            setError(true);
            setFailedCommercial(cr); // store failed CR
          }

          return updated;
        });
      }
    });

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
        console.log("API Error:", err);
        setError(true);
      }
    };

    apiCall();

    return () => frappe.realtime.off("zatca");
  }, []);

  useEffect(() => {
    if (!remainingCrCount) {
      if (completedCrCount === totalCrCount) {
        dispatch(setCurrentPage(200));
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
        {/* Progress Bar */}
        <Progress
          status={
            completedCrCount === totalCrCount
              ? "success"
              : remainingCrCount > 0
              ? "active"
              : "exception"
          }
          className="text-[10px] w-full text-[#f3f3f3]"
          percent={currentPercentage}
          percentPosition={{ align: "center", type: "inner" }}
          size={{ height: 50 }}
          strokeColor="#483f61"
          format={() =>
            remainingCrCount > 0
              ? dataState.commercial_register[completedCrCount]
                  .commercial_register_name
              : "Successfully integrated with ZATCA..."
          }
        />

        {/* Retry Button */}
        {failedCommercial && error ? (
          <div className="my-2">
            <Button onClick={handleRetry} className="bg-[#f3f3f3]">
              Try Again
              <ReloadOutlined />
            </Button>
          </div>
        ) : null}
      </Flex>

      {/* Summary */}
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
