import { useAppSelector } from "@/app/hooks";
import { Button, Flex, Progress } from "antd";
import { useEffect, useState } from "react";

const SocketLoading = () => {
  const [realTimeData, setRealTimeData] = useState<any>({});
  const dataState = useAppSelector((state) => state.dataReducer);

  useEffect(() => {
    if (isDev) return;
    ActivateIO();
  }, []);
  const isError = (cr: any) => {
    const data = realTimeData[cr.commercial_register_number];
    if (data && data.complete && data.indicator === "red") {
      frappe.realtime.off("zatca");
      return true;
    }
    return false;
  };

  const handleRetry = async (cr: any) => {
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

  return (
    <Flex gap={3} className="h-full" vertical>
      <h1 className="text-black text-center font-bold text-2xl">Setting up zatca...</h1>
      {dataState.commercial_register.map((cr) => (
        <Flex
          vertical
          justify="center"
          align="center"
          className="h-full w-full" // Ensure the container takes full width
          gap={2}
          key={cr.commercial_register_number}
        >
          <div>{cr.commercial_register_name}</div>
          <Progress
            status={
              isError(cr)
                ? "exception"
                : realTimeData[cr.commercial_register_number]?.complete
                ? "success"
                : "active"
            }
            className="text-sm w-full text-white" // Ensure the progress bar takes full width
            format={() =>
              isError(cr)
                ? "Error in Zatca Server"
                : realTimeData[cr.commercial_register_number]?.message
            }
            percent={
              realTimeData[cr.commercial_register_number]?.percentage || 0
            }
            percentPosition={{ align: "center", type: "inner" }}
            size={{ height: 50 }}
            strokeColor="#483f61"
          />
          {isError(cr) ? <Button className="w-full" color="danger" onClick={handleRetry}>Retry</Button> : null}
        </Flex>
      ))}
    </Flex>
  );
};

export default SocketLoading;
