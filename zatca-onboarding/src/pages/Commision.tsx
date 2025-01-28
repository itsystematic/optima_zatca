import { useAppDispatch } from "@/app/hooks";
import { setCommission } from "@/data/commission";
import { setCurrentPage } from "@/data/currentPage";
import { Card, Flex, Image, Typography } from "antd";

const Commission = () => {
  const dispatch = useAppDispatch();

  const commissions = [
    {
      id: "main",
      img: !isDev ? "/assets/optima_zatca/zatca-onboarding/MainCommision.png" :"MainCommision.png",
      name: "Main CRN",
    },
    {
      id: "multi",
      img: !isDev ? "/assets/optima_zatca/zatca-onboarding/MultipleCommision.png"  : "MultipleCommision.png",
      name: "Multiple CRNs",
    },
  ];

  const handlePhaseSelect = (commission: string) => {
    dispatch(setCommission({commission}))
    dispatch(setCurrentPage(4));
  };

  return (
    <Flex vertical align="center" className="h-full">
      <Flex className="h-1/3" align="center">
      <Typography.Title className="text-[#483f61]" >{__("Commercial Register Type?")}</Typography.Title>
      </Flex>
      <Flex gap={16} justify="center" align="center" className="mt-6">
        {commissions.map((phase) => (
          <Card
            onClick={() => handlePhaseSelect(phase.id)}
            key={phase.id}
            hoverable
            className="transition-all group bg-[#2a2439] text-white duration-300 w-[180px] h-[180px] flex justify-center items-center rounded-3xl hover:bg-white cursor-pointer hover:text-white border-none"
          >
            <div className="flex justify-center items-center flex-col gap-2">
              <div className="bg-[#d9d9d9] rounded-full w-[70px] h-[70px] group-hover:bg-[#2a2439]">
                <Image
                  preview={false}
                  src={phase.img}
                  width={70}
                  height={70}
                  alt="Expressive Image"
                  className="transition-all duration-300"
                />
              </div>
              <Typography.Text className="text-xl font-medium text-center text-white group-hover:text-[#2a2439]">
                {__(phase.name)}
              </Typography.Text>
            </div>
          </Card>
        ))}
      </Flex>
    </Flex>
  );
};

export default Commission;
